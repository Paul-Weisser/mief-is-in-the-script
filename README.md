## mief-is-in-the-script

To deploy the script on your Raspberry-Pi download our deployment-script (deploy.sh) 

It will create an folder in you home directory called "mief" containing our scripts, create a cronjob, which automatically starts the sensor-app, install python dependencies required for this and activate i2c.
You can so so using wget like:
```
wget https://raw.githubusercontent.com/paul-weisser/mief-is-in-the-script/master/deploy.sh
```
The script will ask you for a pi-id and a pi-secret. You can obtain these from out site `https://mief-is-in-the-air.tk/` by either adding a new pi to your account or obtain an existing via manage.
If you know these yes you can leave it empty and adjust them later in the `apiConfig.json`. 

Enjoy!


