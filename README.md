# Canvas Assignments to iOS Reminders (Outlook Email)

## Outlook
This project automatically get your assignments in your canvas system and send them through email to your iPhone to generate an assignment reminder.

This is how the project works.
1. Polls Canvas every run
2. Sends an email with a JSON payload per new assignment
3. iPhone Shortcuts Automation reads the email and creates a Reminder using the due date

### Prereqs
- Python 3.10+
- Canvas account
- Personal mail account
- iPhone Mail app configured with your mail account

## 1. Setup the Config
To run the project correctly, you need to **create** a `config.json file` and a `course_aliases.json` under the same directory. Take `config.example.json` and `course_aliases.example.json` as examples. To finish the config, you need to provide: *Canvas token*, *mail SMTP password*, *mail SMTP server* to `config.json` and your course aliases of all the courses you will take this semester to `course_aliases.json`. 


### 1.1 Get Canvas Token
1. Log in your **Canvas** https://oc.sjtu.edu.cn. 
2. Click your image on the top left of the page and go to the **profile**. 
3. Enter **setting** on the left bar.
4. Roll down to **Approved Integrations**. 
5. Click **New Access Token**. 
6. Copy the token into the "canvas_token" in `config.json`.


### 1.2 Get Mail SMTP Password
Go to your mail account, activate SMTP service, and ask for your SMTP password. It is often in the account setting page. You can ask AI tools for help. Then copy it into the "smtp_password" in `config.json`.


### 1.3 Get Mail SMTP server
The address of the SMTP server is often in the same page of the SMTP password. Then copy it into the "smtp_host" in `config.json`.


### 1.4 Install Dependencies
Before going to the next step, install dependencies by typing the following codes into the terminal:
```cmd
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```


### 1.5 Set Course Aliases
The origin course name is very long and tedious. Aliases can help to make the reminders clearer. Run the following codes in the terminal to get all the origin course names.
```cmd
python test_canvas_fetch.py
```

Then, edit the `course_aliases.json` as the `course_aliaes.example.json` does. 

***Remind:*** Only those courses written in the `course_aliases.json` will be pushed to your iPhone Reminder.

---

## 2. Set iOS Shortcut Automation
After finishing the config on the PC, you need to create an automated workflow on your iPhone so that when you receive a specific JSON-formatted email, your iPhone will automatically parse the content and create a task in your Reminder App with the correct title and due time.


### 2.1 Import the Shortcut into Your iPhone
Follow the steps to import the `CanvasAssignment.shortcut` into your iPhone.
1. Download the `CanvasAssignment.shortcut` to your iPhone.
2. Open it with **Shortcut** App.
3. Click *Add Shortcut* to add it into your Shortcut App.


### 2.2 Create the Email Automation Trigger
Follow these steps to set up the background trigger that detects incoming emails:
1. Open the **Shortcuts** App on your iPhone.
2. Tap the **Automation** tab at the bottom center of the screen.
3. Tap the **"+"** icon in the top right corner to create a new automation.
4. Scroll down and select **Email**.
5. Configure your trigger conditions:
   * **Sender**: Enter the specific email address that sends the notifications. Refer to *"smtp_from"* in your `config.json`.
   * **Subject Contains**: Enter *CanvasAssignment* to filter out other emails.
   * **Account**: Choose the mail account that receive the email. Refer to *"smtp_to"* in your `config.json`.
6. Under **Run Option**, select **Run Immediately**. This ensures the automation runs completely in the background without asking for manual confirmation.
7. Tap **Next** in the top right corner.


### 2.3: Action Configuration 

Once having created the trigger, it's time for the actions. You can use the CanvasAssginment.shortcut imported to your iPhone as the action directly.

You can use either imported shortcut or add actions manually yourself.

#### Use the Imported Shortcut
Click *CanvasAssignment* under *My Shortcuts*


#### Add Actions Manually
Manually adding actions is also available. Click *Create New Shortcut*. Inside your Blank Automation action editor interface, add the following **6 actions** in this exact order:

##### M1. Parse the Email Body
* **Search and add**: `Get Dictionary from Input`
* **Crucial Setting**: Once added, it defaults to "Get dictionary from `Shortcut Input`". Tap the blue **`Shortcut Input`** variable, scroll down the pop-up menu, and change its type from "Email" to **"text"**.
* *Why? This ensures the system reads only the raw JSON text inside the email body instead of metadata like the sender or subject.*

##### M2. Extract the Course Name
* **Search and add**: `Get Dictionary form Input`
* **Setting**: Type `course_name` into the "Key" field.
* **In the Shortcut**: Get `Value` for `course_name` in `Dictionary`

##### M3. Extract the Assignment Name
* **Search and add**: Add `Get Value from Dictionary` again.
* **Setting**: Type `assignment_name` into the "Key" field.
* **In the Shortcut**: Get `Value` for `assignment_name` in `Dictionary`
* *Note: Ensure its input source links back to the **`Dictionary`** from Step 1.*

##### M4. Extract the Due Date
* **Search and add**: Add `Get Value from Dictionary` one more time.
* **Setting**: Type `due_at` into the "Key" field.
* **In the Shortcut**: Get `Value` for `due_at` in `Dictionary`
* *Note: Ensure its input source links back to the **`Dictionary`** from Step 1.*

##### M5. Convert to Local Time
* **Search and add**: `Get Dates from Input`
* **Setting**: It will automatically connect to the previous step, showing "Get dates from `Dictionary Value`". Make sure that the `Dictionaty Value` is the output of `due_at` in step 4. *(iOS will automatically parse the ISO 8601 UTC time format and convert it natively to your phone's current local time zone).*

##### M6. Create the Reminder
* **Search and add**: `Add New Reminder`
* **Setting**:
  * **Title**: Tap the text field and insert the variables to format it exactly as: `Dictionary Value`- `Dictionary Value`.
  **Remind**:*The first `Dictionaty Value` is the output of `course_name` in step 2. The second `Dictionary Value` is the output of `assignment_name` in step 3.* 
  * Tap the **Expand Arrow (▼)** on the right side of the action to reveal more options.
  * Find **Alert**: Toggle it to **On a Date** (or At Time).
  * Find **Alert Time**: Tap it and choose the **`Dates`** variable generated from Step 5.


---
## 3 Run the Program
Since you have set your pc and your iPhone, you can run your program to push your assignments to your iPhone Reminder. Type these codes into the terminal.
```cmd
python canvas_pushcut.py
```