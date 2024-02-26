### COMANDOS SOPORTADOS
~~~
:Gpt {prompt}
:Gpt ask {prompt}
:Gpt html {url} {prompt}
:Gpt youtube {id} {prompt}
~~~

### SUBCOMANDOS
~~~
- ask:      Para realizar una pregunta.
- html:     Para realizar scraping.
- web:      Para realizar preguntas sobre la propia web.
- youtube:  Para realizar preguntas sobre el propio video. 
- document: Para realizar preguntas sobre el propio documento. 
            Si estas en modo visual, se envia solo la selección
            del documento.

NOTA: todos los resultados se muestran por pantalla y se copian al buffer,
solo con presiona el boton p, podras pegarlo en vim donde gustes.
~~~

### Settings .vimrc, se muestran valores por defecto
~~~
let g:openai_api_base     = 'https://api.openai.com/v1'
let g:openai_api_key      = 'sk-XXX'   
let g:openai_model        = 'gpt-3.5-turbo'
let g:openai_temperature  = '0.5'
let g:llm_youtube_buffer  = '40000'
let g:llm_html_buffer     = '50000'

# Envia el contenido recortado al llm -> youtube_content[0:llm_youtube_buffer]
# Envia el contenido recortado al llm ->    html_content[0:llm_html_buffer]
~~~

### POR CREAR
~~~
:Gpt document  {prompt}
:Gpt web {url} {prompt}
~~~

### DEPENDENCIAS DEL SISTEMA
~~~
- python
- curl
- cat
- ps
~~~
