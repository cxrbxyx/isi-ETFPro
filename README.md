# isi-ETFPro
Para el correcto funcionamiento de la aplicación es necesario obtener el token de seguridad de las APIs utilizadas. Se pueden obtener registrándose en los siguientes enlaces

Alpha Vantage: [https://www.alphavantage.co/](https://www.alphavantage.co/)

Tiingo: [https://www.tiingo.com/](https://www.tiingo.com/)

Una vez obtenidos los tokens, deberán ser introducidos en las variables ALPHA_VANTAGE_API_KEY y TIINGO_API_TOKEN en el archivo app.py

También es necesaria la extensión de Visual Studio Code Live Server para poder ejecutar los html.
# Tutorial de ejecución

Primer paso: crear o utilizar un entorno virtual y ejecutar en la carpeta raiz del proyecto el siguiente comando para instalar las librerías utilizadas

pip install -r requeriments.txt

Segundo paso: ejecutar en la carpeta backend el siguiente comando para ejecutar el servidor de la aplicación

python3 app.py

Tercer paso: Hacer click derecho en el archivo frontend/src/login.html y seleccionar la opción Open with Live Server 

Cuarto paso: Introducir el usuario/contraseña Pablo/1234 o registarse con un nuevo usuario.