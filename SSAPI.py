#Selenium libraries
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

#Data manipulation libraries
from dotenv import load_dotenv
from os import getenv
from bs4 import BeautifulSoup
import json
import datetime
from sys import exit as Exit

#*========================== Downloading Data ========================
def extractCellData(cell, i): # Gets the data from the cell
    if not cell.get("nowrap") == "nowrap":
        return
    data = {
        "rowid": i,    
        "rowspan": 0,   
        "colspan": 0,   
        "info": []      
    }
    if cell.find("span"):
        data["info"] = cell.find("span").encode_contents().decode('UTF-8').replace("\n","").split("<br/>")
    if cell.get("colspan"):
        data["colspan"] = int(cell.get("colspan"))
    if cell.get("rowspan"):
        data["rowspan"] = int(cell.get("rowspan"))
    return data

def returnCells(row, i): # returns only cells which are significant to the schedule
    cells = row.find_all("td", {"class": "schedulecell"})
    row_data = []
    if len(cells) >= 1:
        for cell in cells:
            cell_data = extractCellData(cell, i) # Extract the data from the cell
            if cell_data:
                row_data.append(cell_data)
    return row_data

def getRawData(): # uses selenium to download all the data we need
    chrome_options = Options()
    chrome_options.add_argument("--headless") # this will run the chromedriver invisible

    load_dotenv()
    username = getenv("username")
    password = getenv("password")
    if username == None or password == None:
        print("Write your password and email address in the environment file.")
        with open(".env", "w") as f:
            f.write("username=\npassword=")
        input("exiting...")

        Exit()
    else:
        print("Found username and password in the environment file.")
    url = "https://sms.schoolsoft.se/nti/sso"

    print("Starting Selenium...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options) # this finds the right driver for your system
    driver.get(url)

    username_input = '//*[@id="username"]'
    password_input = '//*[@id="password"]'
    login_button = '/html/body/article/form/div[3]/button'

    print("Logging in...")
    driver.find_element(By.XPATH, username_input).send_keys(username)
    driver.find_element(By.XPATH, password_input).send_keys(password)
    oldUrl = driver.current_url
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, login_button))).click()
    if driver.current_url == oldUrl:
        print("failed to login, exiting...")
        Exit()
    print("Logged in!")

    print("Searching the schedule...")
    schedule_button = '/html/body/div[1]/div/div[2]/div/div/div/a[6]/div'
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, schedule_button))).click()
    print("Schedule found!")
    soup = BeautifulSoup(driver.page_source, "html.parser")
    print("Exiting selenium.")
    driver.quit()
    raw_rows = soup.find_all("tr",{"class": "schedulerow"})

    schedule_rows = {}
    for i in range(len(raw_rows)):
        row_data = returnCells(raw_rows[i], i)
        schedule_rows[i] = row_data

    with open("rawdata.json", "w") as f: # Save the raw data in rawdata.json
        f.write(json.dumps(schedule_rows))
    print("Raw data downloaded.")

    return schedule_rows

#*========================= Converting data ==========================
def getRowspanRanges(cell1,cell2):
    row_start1 = cell1["rowid"]
    row_start2 = cell2["rowid"]
    row_end1 = row_start1 + cell1["rowspan"]
    row_end2 = row_start2 + cell2["rowspan"]
    return row_start1, row_start2, row_end1, row_end2

def checkOverlap(cell1, cell2):
    row_start1, row_start2, row_end1, row_end2 = getRowspanRanges(cell1,cell2)
    return max(row_end1, row_end2) - min(row_start1, row_start2) < (row_end1 - row_start1) + (row_end2 - row_start2) 
    # https://stackoverflow.com/a/25369187/12132452

def getRowspanRemainder(cell1, cell2): # If the lessons overlap we need to add up the remainder of the rowspan, if exists
    row_start1, row_start2, row_end1, row_end2 = getRowspanRanges(cell1,cell2)
    if row_end2 > row_end1:
        return row_end2 - row_end1
    return 0

def addToSchedule(cell, day, schedule, final_schedule):
    if cell["info"]:
        schedule[day].append(cell)
        data = {
            "class": cell["info"][0].replace("\u00e4", "a"),
            "room": cell["info"][2],
            "start": [int(cell["info"][1].split("-")[0].split(":")[0]),int(cell["info"][1].split("-")[0].split(":")[1])],
            "end": [int(cell["info"][1].split("-")[1].split(":")[0]),int(cell["info"][1].split("-")[1].split(":")[1])]
        }
        final_schedule[day].append(data)
    return [schedule, final_schedule]

def convertRawData(schedule_rows = False):

    if not schedule_rows:
        with open("rawdata.json", "r") as f:
            schedule_rows = json.load(f)

    # this is needed to keep track of recorded days rowspan and colspan
    schedule = {"Mon": [], "Tue": [], "Wed": [], "Thu": [], "Fri": []}
    # this is needed to keep track of which day the next lesson/break belongs to
    rowspan_sum = {"Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0}
    # This is the final sorted output
    final_schedule = {"Mon": [], "Tue": [], "Wed": [], "Thu": [],"Fri": []}


    for i,row_data in schedule_rows.items():
        for cell in row_data:
            min_day = min(rowspan_sum, key=rowspan_sum.get) #finds the day with the least rospawn value
            if cell["colspan"] == 4:
                [schedule, final_schedule] = addToSchedule(cell, min_day, schedule, final_schedule)
                rowspan_sum[min_day] += cell["rowspan"]
            else:
                overlap_exists = False
                day = ""
                for possible_day,row_data in schedule.items():
                    if overlap_exists:
                        break
                    for possible_cell in row_data:
                        if checkOverlap(cell, possible_cell) and cell["colspan"] + possible_cell["colspan"] == 4:
                            day = possible_day
                            overlap_exists = True        
                            break
                if overlap_exists:
                    [schedule, final_schedule] = addToSchedule(cell, day, schedule, final_schedule)
                    rowspan_sum[day] += getRowspanRemainder(possible_cell, cell)
                else:
                    [schedule, final_schedule] = addToSchedule(cell, min_day, schedule, final_schedule)
                    rowspan_sum[min_day] += cell["rowspan"]
    print("Saved the schedule.")
    return final_schedule

#*=========================== Manipulating data ========================
def saveData(schedule, use_indent=False):
    with open("schedule.json", "w") as f:
        if use_indent:
            f.write(json.dumps(schedule, indent=2))
        else:
            f.write(json.dumps(schedule))

def getSavedData():
    with open("schedule.json", "r") as f:
        schedule = json.load(f)
    return schedule

def getschedule_today(schedule):
    weekday = datetime.datetime.now().strftime("%A")
    if not(weekday == "Saturday" or weekday == "Sunday"):
        return schedule[weekday[0:3]]
    return False

def log(txt, out): # speciall print function, only allows to print if explicitly said so
    if out: print(txt)

def getCurrentEvent(schedule, out=False):
    now = datetime.datetime.now()
    schedule_today = getschedule_today(schedule)

    if not schedule_today:
        log("It is weekend right now", out)
        return None

    lesson_ongoing = False
    current_lesson = {}
    for lesson in schedule_today:
        lesson_time_start = now.replace(hour=lesson["start"][0], minute=lesson["start"][1], second=0, microsecond=0)
        lesson_time_end = now.replace(hour=lesson["end"][0], minute=lesson["end"][1], second=0, microsecond=0)
        if lesson_time_start <= now and now <= lesson_time_end: #https://stackoverflow.com/a/1831453/12132452
            lesson_ongoing = True
            current_lesson = lesson
            break

    if lesson_ongoing:
        log(f'You have a {current_lesson["class"]} class in {current_lesson["room"]}, which started at {current_lesson["start"][0]}:{current_lesson["start"][1]} and ends at {current_lesson["end"][0]}:{current_lesson["end"][1]}.', out)
        return current_lesson
    log("You have a break right now.", out)
    return None

def getNextEvent(schedule, out=False):
    now = datetime.datetime.now()
    schedule_today = getschedule_today(schedule)

    if not schedule_today:
        schedule_today = schedule["Mon"]
        now = now.replace(weekday="Monday", hour=0, minute=0, second=0, microsecond=0)

    current_lesson = getCurrentEvent(schedule)
    nextLesson = False
    for lesson in schedule_today:
        lesson_time_start = now.replace(hour=lesson["start"][0], minute=lesson["start"][1], second=0, microsecond=0)
        lesson_time_end = now.replace(hour=lesson["end"][0], minute=lesson["end"][1], second=0, microsecond=0)
        if now < lesson_time_start:
            nextLesson = lesson
            break
    
    if nextLesson:
        log(f'You will have a {nextLesson["class"]} class in {nextLesson["room"]}, which starts at {nextLesson["start"][0]}:{nextLesson["start"][1]} and ends at {nextLesson["end"][0]}:{nextLesson["end"][1]}.', out)
        return nextLesson
    log("There is nothing else on your schedule.", out)
    return None

def main():
    saveData(convertRawData(getRawData()), True) #* Downloads the data from SchoolSoft, converts it to a json, and saves it to schedule.json
    # getRawData() # Just downloads the raw data from Schoolsoft using selenium and save it to rawdata.json
    # saveData(convertRawData(), True) #* Just saves the sorted schedule in schedule.json from raw data in rawdata.json

    # getCurrentEvent(getSavedData(), True)
    # getNextEvent(getSavedData(), True)

if __name__ == "__main__":
    main()
    input("Press Enter to exit")