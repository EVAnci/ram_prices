# PC Scraper

> [!NOTE] 
> Este repositorio es de uso personal. El código está realizado y pensado para correr en una computadora portátil con procesador Intel Atom N2600, 4 GB de RAM y conexión WiFi. El sistema operativo utilizado es Arch Linux sin entorno de escritorio (headless) con los paquetes mínimos para tener una distribución funcional.

Este repositorio contiene dos Scrapers Web que funcionan de manera independiente:
- ML web scraper 
- CG web scraper 

Ambos son utilizados para scrapear el precio de componentes de PC, de forma que pueda tomar decisiones de compra inteligentes, analizando precios y usando métricas para detectar descuentos o precios atípicamente bajos.

> [!IMPORTANT] 
> Ambos scripts de scraping deben utilizarse respetando los términos y condiciones de los sitios web implicados. Limite su cantidad de consultas y utilícelo inteligentemente; el autor no se hará responsable de cuentas bloqueadas, IPs baneadas o problemas asociados al mal uso de los scripts.

## Funcionamiento 

Los scrapers están en los siguientes directorios:
- ml_scraper 
- cg_scraper

Cada scraper realiza su tarea de forma diferente. El `cg_scraper` utiliza `requests` ya que se tiene acceso directo a la API. Por otro lado, `ml_scraper` utiliza Playwright para obtener el mismo resultado que se tendría en un navegador web real, parseando el HTML y obteniendo los datos relevantes para su posterior guardado y análisis estadístico.

### cg_scraper 

En este directorio se encuentran múltiples archivos de Python y un archivo de Bash. El archivo llamado `cg_scraper.py` accede a la API de CG usando la librería `requests` y obtiene un JSON de productos que posteriormente procesa y separa los productos que se desean guardar. Adicionalmente, calcula estadísticas básicas sobre los precios diarios, pudiéndose generar un reporte gráfico usando el script `graph_data.py`. Este último script trabaja de forma separada y utiliza los datos guardados en la base de datos para generar un gráfico del precio en función del tiempo usando diagramas de caja y bigotes (media, desviación estándar, máximo y mínimo).

El archivo `run_cg_scraper.sh` es un script de Bash que esencialmente realiza 3 tareas:
1. Verifica la conexión a internet o a una red local según se configure.
2. Corre el script de scraping.
3. Envía el resultado del scraping por correo electrónico.

El primer paso es relevante debido a que está pensado para correr en dispositivos con conexión WiFi sin supervisión, de forma que si la conexión a internet es interrumpida o no está activa, el script pueda ejecutarse en cuanto la conexión se retome.

El archivo `json2html.py` trabaja en conjunto con `run_cg_scraper.sh`, utilizándose para convertir los datos extraídos de la base de datos a una tabla HTML con las estadísticas generales. Luego, esta tabla será enviada por correo según se haya configurado.

### ml_scraper 

El funcionamiento general es muy similar al visto en `cg_scraper`. Se tiene un archivo `ml_scraper.py` que se encarga de realizar el scraping, pero en este caso a través de Playwright. El archivo `db.py` crea la base de datos en donde se depositan diariamente los productos. Este último archivo trabaja en conjunto con `ml_scraper.py`, así que no hay necesidad de ejecutarlo de forma manual.

De la misma manera que en `cg_scraper`, el script de Bash `run_ml_scraper.sh` realiza las mismas tareas pero enfocado en el scraping de otro tipo de componentes. El hecho de que sean dos scripts separados es porque tal vez desee ejecutar más veces uno que otro durante el día. Por ejemplo, podría correr 3 veces `run_cg_scraper.sh` y una sola vez `run_ml_scraper.sh`. De forma análoga, también `ml_mail_report.sh` prepara los datos para enviar por correo en forma de tabla.

> [!IMPORTANT]
> Para que los scripts de bash funcionen correctamente debe crear una regla en /etc/sudoers.d/regla para poder ejecutar los comandos necesarios como sudo sin proporcionar contraseña. Puede seguir el ejemplo siguiente:
```sh 
username ALL=(ALL) NOPASSWD: /usr/bin/ip link set wlp2s0 down, /usr/bin/ip link set wlp2s0 up
```

### Pruebas

Si usted está probando su configuración más primitiva, use los scripts `ml_scraper.py` y `cg_scraper.py` para ejecutar la tarea de scraping y verificar si el resultado es el esperado antes de desplegar todo el servidor automático.

## Despliegue automatizado

El despliegue automatizado tiene por objetivo ejecutar los scripts de scraping de forma cronológica. Esta tarea se lleva a cabo utilizando systemd (mediante los archivos de configuración proporcionados en este mismo repositorio), aunque puede utilizar cualquier programador de tareas como por ejemplo cron, pero usted deberá configurarlo manualmente.

A modo de establecer los requisitos para llevar a cabo el despliegue automático, debe emplear un equipo con Linux, systemd y Python instalado. En particular, esta configuración ha sido probada y pensada para usarse en Arch Linux, pero puede funcionar en otras distribuciones que usen systemd y tengan una configuración similar.

Para comenzar, debe configurar systemd en su sistema operativo. El script `config_env.sh` contiene la configuración de las unidades de systemd (timers y services) encargadas de repetir cronológicamente la tarea de scraping. Antes de ejecutar este script para poder configurar su sistema operativo y las tareas con systemd, use el archivo `env.config.example` como plantilla de ejemplo para crear su archivo `env.config`, el cual tendrá los directorios y nombres de archivos que utilizará para systemd y los scripts de scraping. Luego de crear el archivo `env.config`, debe configurar el cliente de correos `msmtp` con una cuenta o configuración para que el envío de correos de reporte diario sea satisfactorio. Si no desea recibir correos, puede omitir esta parte. También deberá comentar o eliminar las líneas asociadas al envío de correos en los scripts `ml_scraper/run_ml_scraper.sh` y `cg_scraper/run_cg_scraper.sh`. 

Realizado lo anterior, puede ejecutar `config_env.sh`, el cual creará los timers (análogo a las tareas cron) usando systemd. Con esto, el despliegue automático ya ha quedado configurado. 

## Licencia

Este repositorio está sujeto bajo la licencia MIT.
