### mief-is-in-the-script

To deploy the script on your Raspberry Pi download our deployment-script (deploy.sh) 

It will create an folder in you home directory called `mief` containing our scripts, create a cronjob, which automatically starts the sensor-app, install python dependencies required for this and activate i2c.

You can do so using wget like:
```
wget https://raw.githubusercontent.com/paul-weisser/mief-is-in-the-script/master/deploy.sh && chmod +x deploy.sh
```
Now run the script.

The script will ask you for a `pi-id` and a `pi-secret`. You can obtain these from out site `https://mief-is-in-the-air.tk/` by either adding a new pi to your account or obtain the data of an existing via manage.

If you don't know these yet you can leave them empty and adjust them later in the `apiConfig.json`, located in `~/mief`. 


# Config

You can also adjust a offset for the temperature or the humidity in `apiConfig.json` and switch on the debug mode for more detailed logging.

After leaving the file you have to reload the `apiConfig.json`.<br>Therefore you should call:
~~~
pkill -f apiSensor.py
~~~

The script will restart automatically due to the cronjob running in the background, so you wont have to start it manually.

Enjoy!


