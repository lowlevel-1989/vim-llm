import re
import sys
import json
import argparse

WATCH_URL = 'https://www.youtube.com/watch?v={video_id}'

if sys.version_info.major == 3:
    # Para Python 3
    from urllib.request import urlopen
    from urllib.error import URLError
elif sys.version_info.major == 2:
    # Para Python 2
    from urllib2 import urlopen
    from urllib2 import URLError

class HTTP_Client(object):
    def get(self, url):
        return urlopen(url)


# This can only be tested by using different python versions, therefore it is not covered by coverage.py
if sys.version_info.major == 2:  # pragma: no cover
    reload(sys)
    sys.setdefaultencoding('utf-8')


from xml.etree import ElementTree

class CouldNotRetrieveTranscript(Exception):
    """
    Raised if a transcript could not be retrieved.
    """
    ERROR_MESSAGE = '\nCould not retrieve a transcript for the video {video_url}!'
    CAUSE_MESSAGE_INTRO = ' This is most likely caused by:\n\n{cause}'
    CAUSE_MESSAGE = ''
    GITHUB_REFERRAL = (
        '\n\nIf you are sure that the described cause is not responsible for this error '
        'and that a transcript should be retrievable, please create an issue at '
        'https://github.com/jdepoix/youtube-transcript-api/issues. '
        'Please add which version of youtube_transcript_api you are using '
        'and provide the information needed to replicate the error. '
        'Also make sure that there are no open issues which already describe your problem!'
    )

    def __init__(self, video_id):
        self.video_id = video_id
        super(CouldNotRetrieveTranscript, self).__init__(self._build_error_message())

    def _build_error_message(self):
        cause = self.cause
        error_message = self.ERROR_MESSAGE.format(video_url=WATCH_URL.format(video_id=self.video_id))

        if cause:
            error_message += self.CAUSE_MESSAGE_INTRO.format(cause=cause) + self.GITHUB_REFERRAL

        return error_message

    @property
    def cause(self):
        return self.CAUSE_MESSAGE


class YouTubeRequestFailed(CouldNotRetrieveTranscript):
    CAUSE_MESSAGE = 'Request to YouTube failed: {reason}'

    def __init__(self, video_id, http_error):
        self.reason = str(http_error)
        super(YouTubeRequestFailed, self).__init__(video_id)

    @property
    def cause(self):
        return self.CAUSE_MESSAGE.format(
            reason=self.reason,
        )


class VideoUnavailable(CouldNotRetrieveTranscript):
    CAUSE_MESSAGE = 'The video is no longer available'


class InvalidVideoId(CouldNotRetrieveTranscript):
    CAUSE_MESSAGE = (
        'You provided an invalid video id. Make sure you are using the video id and NOT the url!\n\n'
        'Do NOT run: `YouTubeTranscriptApi.get_transcript("https://www.youtube.com/watch?v=1234")`\n'
        'Instead run: `YouTubeTranscriptApi.get_transcript("1234")`'
    )


class TooManyRequests(CouldNotRetrieveTranscript):
    CAUSE_MESSAGE = (
        'YouTube is receiving too many requests from this IP and now requires solving a captcha to continue. '
        'One of the following things can be done to work around this:\n\
        - Manually solve the captcha in a browser and export the cookie. '
        'Read here how to use that cookie with '
        'youtube-transcript-api: https://github.com/jdepoix/youtube-transcript-api#cookies\n\
        - Use a different IP address\n\
        - Wait until the ban on your IP has been lifted'
    )


class TranscriptsDisabled(CouldNotRetrieveTranscript):
    CAUSE_MESSAGE = 'Subtitles are disabled for this video'


class NoTranscriptAvailable(CouldNotRetrieveTranscript):
    CAUSE_MESSAGE = 'No transcripts are available for this video'


class NotTranslatable(CouldNotRetrieveTranscript):
    CAUSE_MESSAGE = 'The requested language is not translatable'


class TranslationLanguageNotAvailable(CouldNotRetrieveTranscript):
    CAUSE_MESSAGE = 'The requested translation language is not available'


class CookiePathInvalid(CouldNotRetrieveTranscript):
    CAUSE_MESSAGE = 'The provided cookie file was unable to be loaded'


class CookiesInvalid(CouldNotRetrieveTranscript):
    CAUSE_MESSAGE = 'The cookies provided are not valid (may have expired)'


class FailedToCreateConsentCookie(CouldNotRetrieveTranscript):
    CAUSE_MESSAGE = 'Failed to automatically give consent to saving cookies'


class NoTranscriptFound(CouldNotRetrieveTranscript):
    CAUSE_MESSAGE = (
        'No transcripts were found for any of the requested language codes: {requested_language_codes}\n\n'
        '{transcript_data}'
    )

    def __init__(self, video_id, requested_language_codes, transcript_data):
        self._requested_language_codes = requested_language_codes
        self._transcript_data = transcript_data
        super(NoTranscriptFound, self).__init__(video_id)

    @property
    def cause(self):
        return self.CAUSE_MESSAGE.format(
            requested_language_codes=self._requested_language_codes,
            transcript_data=str(self._transcript_data),
        )

class Formatter(object):
    """Formatter should be used as an abstract base class.

    Formatter classes should inherit from this class and implement
    their own .format() method which should return a string. A
    transcript is represented by a List of Dictionary items.
    """

    def format_transcript(self, transcript, **kwargs):
        raise NotImplementedError('A subclass of Formatter must implement ' \
            'their own .format_transcript() method.')

    def format_transcripts(self, transcripts, **kwargs):
        raise NotImplementedError('A subclass of Formatter must implement ' \
                                  'their own .format_transcripts() method.')


class TextFormatter(Formatter):
    def format_transcript(self, transcript, **kwargs):
        """Converts a transcript into plain text with no timestamps.

        :param transcript:
        :return: all transcript text lines separated by newline breaks.'
        :rtype str
        """
        return '\n'.join(line['text'] for line in transcript)

    def format_transcripts(self, transcripts, **kwargs):
        """Converts a list of transcripts into plain text with no timestamps.

        :param transcripts:
        :return: all transcript text lines separated by newline breaks.'
        :rtype str
        """
        return '\n\n\n'.join([self.format_transcript(transcript, **kwargs) for transcript in transcripts])

class _TextBasedFormatter(TextFormatter):
    def _format_timestamp(self, hours, mins, secs, ms):
        raise NotImplementedError('A subclass of _TextBasedFormatter must implement ' \
            'their own .format_timestamp() method.')

    def _format_transcript_header(self, lines):
        raise NotImplementedError('A subclass of _TextBasedFormatter must implement ' \
            'their own _format_transcript_header method.')

    def _format_transcript_helper(self, i, time_text, line):
        raise NotImplementedError('A subclass of _TextBasedFormatter must implement ' \
            'their own _format_transcript_helper method.')

    def _seconds_to_timestamp(self, time):
        """Helper that converts `time` into a transcript cue timestamp.

        :reference: https://www.w3.org/TR/webvtt1/#webvtt-timestamp

        :param time: a float representing time in seconds.
        :type time: float
        :return: a string formatted as a cue timestamp, 'HH:MM:SS.MS'
        :rtype str
        :example:
        >>> self._seconds_to_timestamp(6.93)
        '00:00:06.930'
        """
        time = float(time)
        hours_float, remainder = divmod(time, 3600)
        mins_float, secs_float = divmod(remainder, 60)
        hours, mins, secs = int(hours_float), int(mins_float), int(secs_float)
        ms = int(round((time - int(time))*1000, 2))
        return self._format_timestamp(hours, mins, secs, ms)

    def format_transcript(self, transcript, **kwargs):
        """A basic implementation of WEBVTT/SRT formatting.

        :param transcript:
        :reference:
        https://www.w3.org/TR/webvtt1/#introduction-caption
        https://www.3playmedia.com/blog/create-srt-file/
        """
        lines = []
        for i, line in enumerate(transcript):
            end = line['start'] + line['duration']
            time_text = "{} > {}".format(
                self._seconds_to_timestamp(line['start']),
                self._seconds_to_timestamp(
                    transcript[i + 1]['start']
                    if i < len(transcript) - 1 and transcript[i + 1]['start'] < end else end
                )
            )
            lines.append(self._format_transcript_helper(i, time_text, line))

        return self._format_transcript_header(lines)

class AIFormatter(_TextBasedFormatter):
    def _format_timestamp(self, hours, mins, secs, ms):
        return "{:02d}:{:02d}:{:02d}".format(hours, mins, secs)

    def _format_transcript_header(self, lines):
        return "".join(lines)

    def _format_transcript_helper(self, i, time_text, line):
        return "\n{}\n{}".format(time_text, line['text'])


class SRTFormatter(_TextBasedFormatter):
    def _format_timestamp(self, hours, mins, secs, ms):
        return "{:02d}:{:02d}:{:02d},{:03d}".format(hours, mins, secs, ms)

    def _format_transcript_header(self, lines):
        return "\n\n".join(lines) + "\n"

    def _format_transcript_helper(self, i, time_text, line):
        return "{}\n{}\n{}".format(i + 1, time_text, line['text'])


# This can only be tested by using different python versions, therefore it is not covered by coverage.py
if sys.version_info.major == 3 and sys.version_info.minor >= 4: # pragma: no cover
    # Python 3.4+
    from html import unescape
else: # pragma: no cover
    if sys.version_info.major <= 2:
        # Python 2
        import HTMLParser

        html_parser = HTMLParser.HTMLParser()
    else:
        # Python 3.0 - 3.3
        import html.parser

        html_parser = html.parser.HTMLParser()

    def unescape(string):
        return html_parser.unescape(string)

class TranscriptListFetcher(object):
    def __init__(self, http_client):
        self._http_client = http_client

    def fetch(self, video_id):
        return TranscriptList.build(
            self._http_client,
            video_id,
            self._extract_captions_json(self._fetch_video_html(video_id), video_id),
        )

    def _extract_captions_json(self, html, video_id):
        splitted_html = html.split('"captions":')

        if len(splitted_html) <= 1:
            if video_id.startswith('http://') or video_id.startswith('https://'):
                raise InvalidVideoId(video_id)
            if 'class="g-recaptcha"' in html:
                raise TooManyRequests(video_id)
            if '"playabilityStatus":' not in html:
                raise VideoUnavailable(video_id)

            raise TranscriptsDisabled(video_id)

        captions_json = json.loads(
            splitted_html[1].split(',"videoDetails')[0].replace('\n', '')
        ).get('playerCaptionsTracklistRenderer')
        if captions_json is None:
            raise TranscriptsDisabled(video_id)

        if 'captionTracks' not in captions_json:
            raise NoTranscriptAvailable(video_id)

        return captions_json

    def _fetch_video_html(self, video_id):
        html = self._fetch_html(video_id)
        if 'action="https://consent.youtube.com/s"' in html:
            html = self._fetch_html(video_id)
            if 'action="https://consent.youtube.com/s"' in html:
                raise FailedToCreateConsentCookie(video_id)
        return html

    def _fetch_html(self, video_id):
        response = self._http_client.get(WATCH_URL.format(video_id=video_id))
        return response.read().decode('utf-8')


class TranscriptList(object):
    """
    This object represents a list of transcripts. It can be iterated over to list all transcripts which are available
    for a given YouTube video. Also it provides functionality to search for a transcript in a given language.
    """

    def __init__(self, video_id, manually_created_transcripts, generated_transcripts, translation_languages):
        """
        The constructor is only for internal use. Use the static build method instead.

        :param video_id: the id of the video this TranscriptList is for
        :type video_id: str
        :param manually_created_transcripts: dict mapping language codes to the manually created transcripts
        :type manually_created_transcripts: dict[str, Transcript]
        :param generated_transcripts: dict mapping language codes to the generated transcripts
        :type generated_transcripts: dict[str, Transcript]
        :param translation_languages: list of languages which can be used for translatable languages
        :type translation_languages: list[dict[str, str]]
        """
        self.video_id = video_id
        self._manually_created_transcripts = manually_created_transcripts
        self._generated_transcripts = generated_transcripts
        self._translation_languages = translation_languages

    @staticmethod
    def build(http_client, video_id, captions_json):
        """
        Factory method for TranscriptList.

        :param http_client: http client which is used to make the transcript retrieving http calls
        :type http_client: requests.Session
        :param video_id: the id of the video this TranscriptList is for
        :type video_id: str
        :param captions_json: the JSON parsed from the YouTube pages static HTML
        :type captions_json: dict
        :return: the created TranscriptList
        :rtype TranscriptList:
        """
        translation_languages = [
            {
                'language': translation_language['languageName']['simpleText'],
                'language_code': translation_language['languageCode'],
            } for translation_language in captions_json.get('translationLanguages', [])
        ]

        manually_created_transcripts = {}
        generated_transcripts = {}

        for caption in captions_json['captionTracks']:
            if caption.get('kind', '') == 'asr':
                transcript_dict = generated_transcripts
            else:
                transcript_dict = manually_created_transcripts

            transcript_dict[caption['languageCode']] = Transcript(
                http_client,
                video_id,
                caption['baseUrl'],
                caption['name']['simpleText'],
                caption['languageCode'],
                caption.get('kind', '') == 'asr',
                translation_languages if caption.get('isTranslatable', False) else [],
            )

        return TranscriptList(
            video_id,
            manually_created_transcripts,
            generated_transcripts,
            translation_languages,
        )

    def __iter__(self):
        return iter(list(self._manually_created_transcripts.values()) + list(self._generated_transcripts.values()))

    def find_transcript(self, language_codes):
        """
        Finds a transcript for a given language code. Manually created transcripts are returned first and only if none
        are found, generated transcripts are used. If you only want generated transcripts use
        `find_manually_created_transcript` instead.

        :param language_codes: A list of language codes in a descending priority. For example, if this is set to
        ['de', 'en'] it will first try to fetch the german transcript (de) and then fetch the english transcript (en) if
        it fails to do so.
        :type languages: list[str]
        :return: the found Transcript
        :rtype Transcript:
        :raises: NoTranscriptFound
        """
        return self._find_transcript(language_codes, [self._manually_created_transcripts, self._generated_transcripts])

    def find_generated_transcript(self, language_codes):
        """
        Finds an automatically generated transcript for a given language code.

        :param language_codes: A list of language codes in a descending priority. For example, if this is set to
        ['de', 'en'] it will first try to fetch the german transcript (de) and then fetch the english transcript (en) if
        it fails to do so.
        :type languages: list[str]
        :return: the found Transcript
        :rtype Transcript:
        :raises: NoTranscriptFound
        """
        return self._find_transcript(language_codes, [self._generated_transcripts])

    def find_manually_created_transcript(self, language_codes):
        """
        Finds a manually created transcript for a given language code.

        :param language_codes: A list of language codes in a descending priority. For example, if this is set to
        ['de', 'en'] it will first try to fetch the german transcript (de) and then fetch the english transcript (en) if
        it fails to do so.
        :type languages: list[str]
        :return: the found Transcript
        :rtype Transcript:
        :raises: NoTranscriptFound
        """
        return self._find_transcript(language_codes, [self._manually_created_transcripts])

    def _find_transcript(self, language_codes, transcript_dicts):
        for language_code in language_codes:
            for transcript_dict in transcript_dicts:
                if language_code in transcript_dict:
                    return transcript_dict[language_code]

        raise NoTranscriptFound(
            self.video_id,
            language_codes,
            self
        )

    def __str__(self):
        return (
            'For this video ({video_id}) transcripts are available in the following languages:\n\n'
            '(MANUALLY CREATED)\n'
            '{available_manually_created_transcript_languages}\n\n'
            '(GENERATED)\n'
            '{available_generated_transcripts}\n\n'
            '(TRANSLATION LANGUAGES)\n'
            '{available_translation_languages}'
        ).format(
            video_id=self.video_id,
            available_manually_created_transcript_languages=self._get_language_description(
                str(transcript) for transcript in self._manually_created_transcripts.values()
            ),
            available_generated_transcripts=self._get_language_description(
                str(transcript) for transcript in self._generated_transcripts.values()
            ),
            available_translation_languages=self._get_language_description(
                '{language_code} ("{language}")'.format(
                    language=translation_language['language'],
                    language_code=translation_language['language_code'],
                ) for translation_language in self._translation_languages
            )
        )

    def _get_language_description(self, transcript_strings):
        description = '\n'.join(' - {transcript}'.format(transcript=transcript) for transcript in transcript_strings)
        return description if description else 'None'


class Transcript(object):
    def __init__(self, http_client, video_id, url, language, language_code, is_generated, translation_languages):
        """
        You probably don't want to initialize this directly. Usually you'll access Transcript objects using a
        TranscriptList.

        :param http_client: http client which is used to make the transcript retrieving http calls
        :type http_client: requests.Session
        :param video_id: the id of the video this TranscriptList is for
        :type video_id: str
        :param url: the url which needs to be called to fetch the transcript
        :param language: the name of the language this transcript uses
        :param language_code:
        :param is_generated:
        :param translation_languages:
        """
        self._http_client = http_client
        self.video_id = video_id
        self._url = url
        self.language = language
        self.language_code = language_code
        self.is_generated = is_generated
        self.translation_languages = translation_languages
        self._translation_languages_dict = {
            translation_language['language_code']: translation_language['language']
            for translation_language in translation_languages
        }

    def fetch(self, preserve_formatting=False):
        """
        Loads the actual transcript data.
        :param preserve_formatting: whether to keep select HTML text formatting
        :type preserve_formatting: bool
        :return: a list of dictionaries containing the 'text', 'start' and 'duration' keys
        :rtype [{'text': str, 'start': float, 'end': float}]:
        """
        response = self._http_client.get(self._url)
        return _TranscriptParser(preserve_formatting=preserve_formatting).parse(
            response.read().decode('utf-8'),
        )

    def __str__(self):
        return '{language_code} ("{language}"){translation_description}'.format(
            language=self.language,
            language_code=self.language_code,
            translation_description='[TRANSLATABLE]' if self.is_translatable else ''
        )

    @property
    def is_translatable(self):
        return len(self.translation_languages) > 0

    def translate(self, language_code):
        if not self.is_translatable:
            raise NotTranslatable(self.video_id)

        if language_code not in self._translation_languages_dict:
            raise TranslationLanguageNotAvailable(self.video_id)

        return Transcript(
            self._http_client,
            self.video_id,
            '{url}&tlang={language_code}'.format(url=self._url, language_code=language_code),
            self._translation_languages_dict[language_code],
            language_code,
            True,
            [],
        )


class _TranscriptParser(object):
    _FORMATTING_TAGS = [
        'strong',  # important
        'em',  # emphasized
        'b',  # bold
        'i',  # italic
        'mark',  # marked
        'small',  # smaller
        'del',  # deleted
        'ins',  # inserted
        'sub',  # subscript
        'sup',  # superscript
    ]

    def __init__(self, preserve_formatting=False):
        self._html_regex = self._get_html_regex(preserve_formatting)

    def _get_html_regex(self, preserve_formatting):
        if preserve_formatting:
            formats_regex = '|'.join(self._FORMATTING_TAGS)
            formats_regex = r'<\/?(?!\/?(' + formats_regex + r')\b).*?\b>'
            html_regex = re.compile(formats_regex, re.IGNORECASE)
        else:
            html_regex = re.compile(r'<[^>]*>', re.IGNORECASE)
        return html_regex

    def parse(self, plain_data):
        return [
            {
                'text': re.sub(self._html_regex, '', unescape(xml_element.text)),
                'start': float(xml_element.attrib['start']),
                'duration': float(xml_element.attrib.get('dur', '0.0')),
            }
            for xml_element in ElementTree.fromstring(plain_data)
            if xml_element.text is not None
        ]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='YouTube Transcript/Subtitle from HTML')
    parser.add_argument('--id', help='the path to a file to sanitize')
    args = parser.parse_args()

    http_client = HTTP_Client()
    transcripts = TranscriptListFetcher(http_client).fetch(args.id).find_transcript(['en', 'es', 'ja']).fetch()
    print(AIFormatter().format_transcripts([transcripts]))

