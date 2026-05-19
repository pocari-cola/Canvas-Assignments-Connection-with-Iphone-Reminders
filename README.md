# Canvas Assignments to iOS Reminders (Outlook Email)

## What it does
- Polls Canvas every run
- Sends an email with a JSON payload per new assignment
- iPhone Shortcuts Automation reads the email and creates a Reminder using the due date

## Prereqs
- Python 3.10+
- Canvas API token
- Personal mail account
- iPhone Mail app configured with your mail account

## Setup (Mail SMTP)
**1. Get the password:**
   Get the SMTP password of your mail account.
   Get your Canvas token: Log in your **canvas**. Click your image on the top right of the page and go to the **profile**. Enter **setting** and go to **Approved Integrations**. Click **New Access Token**. 

**2. Edit course_aliases.json**
   Edit course_aliases.json to map Canvas course names to short labels. Remind that only courses in the aliases list will be pushed to the reminder.

**3. Edit config.json**
   Copy config.example.json to config.json and fill in the values of your own.

**4. Install dependencies:**
   - `python -m venv .venv`
   - `.\.venv\Scripts\activate`
   - `pip install -r requirements.txt`

**5. Run the script:**
   - python canvas_pushcut.py

## Testing Files
**tese_canvas_fetch.py**
   Run the file to check if the canvas fetch works.

**test_smtp_connection.py**
   Run the file to check if your connection to the mail account works.

## Generated Files
**assignment.json**
   A record of all the assignments in your current canvas.

**state.json**
   ID of the assignments that has already pushed to the iphone.


# iOS Shortcut Automation Guide: Email to Reminders

This guide will help you create an automated workflow on your iPhone. When you receive a specific JSON-formatted email, your iPhone will automatically parse the content and create a task in your **Reminders** App with the correct title and local due time.

---

## Part 1: How to Create the Email Automation Trigger

Follow these steps to set up the background trigger that detects incoming emails:

1. Open the **Shortcuts** App on your iPhone.
2. Tap the **Automation** tab at the bottom center of the screen.
3. Tap the **"+"** icon in the top right corner to create a new automation.
4. Scroll down and select **Email**.
5. Configure your trigger conditions:
   * **Sender**: Enter the specific email address that sends the notifications.
   * **Subject Contains**: *(Optional)* Enter a specific prefix or keyword (e.g., `CanvasAssignment`) to filter out other emails.
6. Under **Run Option**, select **Run Immediately**. *(Crucial: This ensures the automation runs completely in the background without asking for manual confirmation).*
7. Tap **Next** in the top right corner, then choose **New Blank Automation**.

---

## Part 2: Step-by-Step Action Configuration (iOS English System)

Inside your Blank Automation action editor interface, search for and add the following **6 actions** in this exact order:

### 1. Parse the Email Body
* **Search and add**: `Get Dictionary from Input`
* **Crucial Setting**: Once added, it defaults to "Get dictionary from `Shortcut Input`". Tap the blue **`Shortcut Input`** variable, scroll down the pop-up menu, and change its type from "Email" to **"text"**.
* *Why? This ensures the system reads only the raw JSON text inside the email body instead of metadata like the sender or subject.*

### 2. Extract the Course Name
* **Search and add**: `Get Dictionary form Input`
* **Setting**: Type `course_name` into the "Key" field.
* **In the Shortcut**: Get `Value` for `course_name` in `Dictionary`

### 3. Extract the Assignment Name
* **Search and add**: Add `Get Value from Dictionary` again.
* **Setting**: Type `assignment_name` into the "Key" field.
* **In the Shortcut**: Get `Value` for `assignment_name` in `Dictionary`
* *Note: Ensure its input source links back to the **`Dictionary`** from Step 1.*

### 4. Extract the Due Date
* **Search and add**: Add `Get Value from Dictionary` one more time.
* **Setting**: Type `due_at` into the "Key" field.
* **In the Shortcut**: Get `Value` for `due_at` in `Dictionary`
* *Note: Ensure its input source links back to the **`Dictionary`** from Step 1.*

### 5. Convert to Local Time
* **Search and add**: `Get Dates from Input`
* **Setting**: It will automatically connect to the previous step, showing "Get dates from `Dictionary Value`". Make sure that the `Dictionaty Value` is the output of `due_at` in step 4. *(iOS will automatically parse the ISO 8601 UTC time format and convert it natively to your phone's current local time zone).*

### 6. Create the Reminder
* **Search and add**: `Add New Reminder`
* **Setting**:
  * **Title**: Tap the text field and insert the variables to format it exactly as: `Dictionary Value`- `Dictionary Value`.
  **Remind**:*The first `Dictionaty Value` is the output of `course_name` in step 2. The second `Dictionary Value` is the output of `assignment_name` in step 3.* 
  * Tap the **Expand Arrow (▼)** on the right side of the action to reveal more options.
  * Find **Alert**: Toggle it to **On a Date** (or At Time).
  * Find **Alert Time**: Tap it and choose the **`Dates`** variable generated from Step 5.

