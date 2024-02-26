"
" Comandos soportados de momento
"
" :Gpt prompt
" :Gpt ask prompt
" :Gpt html {url} prompt
" :Gpt web  {url} prompt
" :Gpt youtube {id} prompt
"
" TODO: por denifir, consulta de documento
"
" :Gpt document prompt


" command! -nargs=+ Gemini :call ParserInputPrompt('gemini', <q-args>)
command! -nargs=+ Gpt    :call ParserInputPrompt('gpt',    <q-args>)
command! -nargs=+ GPT    :call ParserInputPrompt('gpt',    <q-args>)

" let s:gemini_api_key  = get(g:, 'gemini_api_key',  trim(system('echo $GEMINI_API_KEY')))

let s:openai_api_base     = get(g:, 'openai_api_base',       'https://api.openai.com/v1')
let s:openai_api_key      = get(g:, 'openai_api_key',        trim(system('echo $OPENAI_API_KEY')))
let s:openai_model        = get(g:, 'openai_model',          'gpt-3.5-turbo')
let s:openai_temperature  = str2float(get(g:, 'openai_temperature',    '0.5'))

" Envia el contenido recortado al llm -> youtube_content[0:llm_youtube_buffer]
" Envia el contenido recortado al llm ->    html_content[0:llm_html_buffer]
let s:llm_youtube_buffer   = str2nr(get(g:, 'llm_youtube_buffer',  '40000'))
let s:llm_html_buffer      = str2nr(get(g:, 'llm_html_buffer',     '50000'))

" Descomentar para pruebas
" let s:openai_api_base = 'http://127.0.0.1:4405'

let s:loading_finished = 1
let s:loading_index    = 0

let s:exec_sanitizer_vanilla   = findfile('sanitizer_vanilla.py',                  expand('<sfile>:p:h'))
let s:exec_youtube_transcripts = findfile('youtube-transcript-api/transcripts.py', expand('<sfile>:p:h'))

" Define la logica de entrada para los sub comandos
let s:SUB_COMMANDS = {
    \ 'ask':      'LLMGemerate',
    \ 'html':     'LLMGemerate',
    \ 'youtube':  'LLMGemerate'
    \ }

" Define la logica de la consulta por llm
let s:LLM_COMMANDS = {
      \ 'gpt': {
          \ 'ask':     'GPTCommandAsk',
          \ 'html':    'GPTCommandHTML',
          \ 'youtube': 'GPTCommandYoutube'
      \ }
    \ }

" Render la animación de loading
function Loading(llm, ...)
  let indicators = ['\', '|', '/', '-']

  if s:loading_finished == 1
    let s:loading_index = 0
    return
  endif

  redraw!
  echon '['.a:llm.'] Loading ' . indicators[s:loading_index] . ' .'

  let s:loading_index = (s:loading_index + 1) % len(indicators)
endfunction

" Espera a que termine la ejecución de un pid
" Se utiliza para el seguimiento en procesos en background
function Wait(pid)
  while 1
    let wait = system('ps -p '. trim(a:pid) . ' > /dev/null 2>&1; echo $?')
    if wait == 1
      break
    endif
    sleep 100ms
  endwhile
endfunction

" Ayuda para descargar HTML
function DownloadURL(url, outfile)
  let curl_command = 'curl --silent -X GET ' .
    \ ' -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" ' .
    \ '"' . a:url . '" > ' . a:outfile
  return system(curl_command . ' & echo $!')
endfunction

" Entrada principal del comando
function! ParserInputPrompt(llm, raw_input)
  let raw_input = split(a:raw_input, ' ')

  let sub_command_id = tolower(raw_input[0])
  let sub_command    = get(s:SUB_COMMANDS, sub_command_id, 0)

  let s:loading_finished = 0
  let loading = timer_start(100, {-> Loading(a:llm)}, {'repeat': -1})

  " Permito generar llamadas a diferentes funciones definidas en SUB_COMMANDS
  if !empty(sub_command)
    let SubCommand = function(sub_command)
    let prompt   = raw_input[1:]
    let response = SubCommand(a:llm,    sub_command_id, prompt)
  else
    let prompt    = raw_input
    let response  = LLMGemerate(a:llm, 'ask', prompt)
  endif

  let s:loading_finished = 1
  call timer_stop(loading)

  redraw!

  call setreg('', response)
  echo response

  " El primero es por comodidad
  echo ' '
  call input('Press 2 ENTER to continue ')
  call input('Press 1 ENTER to continue ')
endfunction

function GPTGenerateRequest(payload, outfile)
  let curl_command = 'curl --silent -X POST ' .
    \ '-H "Content-Type: application/json" ' .
    \ '-H "Authorization: Bearer ' . s:openai_api_key . '" ' .
    \ '-d ' . shellescape(json_encode(a:payload)) . ' ' .
    \ s:openai_api_base . '/chat/completions > ' . a:outfile

  return curl_command
endfunction

function GPTGeneratePayloadAsk(prompt)
  let payload = {
    \ 'model': s:openai_model,
    \ 'messages': [],
    \ 'temperature': s:openai_temperature
    \ }

  for chunk in a:prompt
    call add(payload['messages'], {'role': 'user', 'content': chunk})
  endfo

  return payload
endfunction

function GPTCommandRaw(payload, outfile)
  let curl_command = GPTGenerateRequest(a:payload, a:outfile)
  return system(curl_command . ' & echo $!')
endfunction

function GPTCommandAsk(prompt, outfile)
  let prompt       = join(a:prompt, ' ')
  let payload      = GPTGeneratePayloadAsk([prompt])
  return GPTCommandRaw(payload, a:outfile)
endfunction

function SplitChunks(string)
    let result = []
    let len = strlen(a:string)

    " 4 caracteres son mas o menos 1 token
    for i in range(0, len - 1, 4 * 1000)
        let chunk = strpart(a:string, i, 4 * 1000)
        call add(result, chunk)
    endfor

    return result
endfunction

function GPTCommandYoutube(prompt, outfile)
  let id          = a:prompt[0]
  let prompt      = join(a:prompt[1:], ' ')

  let transcripts = system('python '. s:exec_youtube_transcripts .' --id ' . id)
  let transcripts = substitute(transcripts, '\n\+', '', 'g')

  " Guardamos los primeros 40k
  " Por solucionar para que sean tokens y no caracteres
  let chunks = SplitChunks(transcripts[0:s:llm_youtube_buffer])

  let payload = GPTGeneratePayloadAsk(['video id: '. id . "```video\n"] + chunks + ["``` \n\n" . prompt])
  return GPTCommandRaw(payload, a:outfile)
endfunction

function GPTCommandHTML(prompt, outfile)
  let outfile_url = tempname()
  let url     = a:prompt[0]
  let prompt  = join(a:prompt[1:], ' ')

  let pid = DownloadURL(url, outfile_url)

  " esperamos que termine la ejecución del curl
  call Wait(pid)

  " leemos la salida del curl
  let html_content = system('cat ' . outfile_url)

  call delete(outfile_url)

  " Eliminar espacios en blanco innecesarios
  let html_content = substitute(html_content, '\s\+', ' ', 'g')
  let html_content = substitute(html_content, '\n\+', '\n', 'g')

  " Solo por si lo quiero comentar, lo coloco y mantengo el de arriba
  let html_content = substitute(html_content, '\n\+', '', 'g')

  let html_content = substitute(html_content, '<link[^>]*href=[^>]*>',  '', 'g')
  let html_content = substitute(html_content, '<svg .*></svg>',         '', 'g')

  let html_content = substitute(html_content, '<style.*>\(.\{-}\)</style>', '', 'g')
  let html_content = substitute(html_content, '<script>\(.\{-}\)</script>', '', 'g')
  let html_content = substitute(html_content, '<script[^>]*type=''text/javascript''[^>]*>\(.\{-}\)</script>', '', 'g')
  let html_content = substitute(html_content, '<script[^>]*type="text/javascript"[^>]*>\(.\{-}\)</script>', '', 'g')
  let html_content = substitute(html_content, '<script[^>]*src=[^>]*>\(.\{-}\)</script>', '', 'g')

  " Eliminar todos los scripts que no tengan definido el atributo type
  " TODO: A futuro eliminar dependencia de python
  let html_file_tmp = tempname()
  call writefile(split(html_content, '\n'), html_file_tmp)
  let html_content = ''
  let html_content = system('python '. s:exec_sanitizer_vanilla  .' --file ' . html_file_tmp)
  call delete(html_file_tmp)


  " Aseguramos un maximo de 50k por solicitud por curl
  " La verdad curl soporta hasta mas de 100k pero tenemos que validar los
  " tokens maximos
  " Guardamos los primeros 50k
  " Por solucionar para que sean tokens y no caracteres
  let html_content = html_content[0:s:llm_html_buffer]

  let chunks = ['url: ' . url . " \n " . '```html' . " \n "]
  let chunks = chunks + SplitChunks(html_content)
  let chunks = chunks + [ " \n " . '```' . " \n\n ", prompt]

  let payload = GPTGeneratePayloadAsk(chunks)
  return GPTCommandRaw(payload, a:outfile)

endfunction

function LLMGemerate(llm, sub_command_id, prompt)
  let outfile = tempname()

  let llm_command = get(s:LLM_COMMANDS[a:llm], a:sub_command_id, 0)

  if empty(llm_command)
    call delete(outfile)
    return 'WARN: Working progress'
  endif

  let LLMClient = function(llm_command)

  let pid = LLMClient(a:prompt, outfile)

  " esperamos que termine la ejecución del curl
  call Wait(pid)

  " leemos la salida del curl
  let response = system('cat ' . outfile)

  if a:llm == 'gpt'
    let response = json_decode(response)['choices'][0]['message']['content']
  endif

  call delete(outfile)

  return response

endfunction
