# SchoolSoft-API

This project is used to download the schedule data from SchoolSoft for students.

## How to use

(Un)Comment the functions you want the script to run following functions:

```python
saveData(convertRawData(getRawData()), True) #* Downloads the data from SchoolSoft, converts it to a json, and saves it to schedule.json
getRawData() # Just downloads the raw data from Schoolsoft using selenium and save it to rawdata.json
saveData(convertRawData(), True) #* Just saves the sorted schedule in schedule.json from raw data in rawdata.json

#These 2 functions are used to showcase what you can do with this script
getCurrentEvent(getSavedData(), True)
getNextEvent(getSavedData(), True)
```

- (Optional) compile the script (use py2exe, auto-py-to-exe is having problems with python 3.10)
- Run the script first time, it's going to create .env file
- Fill in the .env file with your login username and password
- Run the script again

## Notes

Tested on Windows 10 with python 3.10
The script doesn't work with schedules where there are 3 or more lessons overlapping.
This has only been tested with my schedule yet
