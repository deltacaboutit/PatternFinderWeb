# Pattern Finder for iPhone

This is the phone version of Pattern Finder. It uses exactly the same pattern-finding math as the Windows app, but it runs as a web page. You put it online once (free), then save it to your iPhone home screen. After that it opens like a normal app, with its own icon.

> This is a learning and research tool, not financial advice.

---

## Part 1: Put the app online (about 15 minutes, done once)

You will use two free websites:

* **GitHub** stores the app's files.
* **Streamlit Community Cloud** runs the app and gives you a web address for it.

You can do all of this on your Windows PC.

### Step 1: Make a GitHub account
1. Go to <https://github.com/signup> and create a free account.

### Step 2: Upload the app's files to GitHub
1. Unzip this folder on your PC.
2. On GitHub, click the **+** button at the top right, then **New repository**.
   * A "repository" is just a folder on GitHub.
3. Fill in the form:
   * **Repository name**: `pattern-finder`
   * Leave it set to **Public**. The code has no passwords or personal data in it.
4. Click **Create repository**.
5. On the next page, click the link **uploading an existing file**.
6. Open the unzipped folder on your PC. Select **everything inside it**: press Ctrl+A, then drag it all onto the GitHub page.
   * Upload the files inside the folder, not the folder itself.
   * `streamlit_app.py` must end up at the top level.
7. Wait for the files to finish uploading, then click the green **Commit changes** button at the bottom.

### Step 3: Start the app on Streamlit Community Cloud
1. Go to <https://share.streamlit.io> and click **Continue with GitHub**. Allow it to connect to your GitHub account.
2. Click **Create app**.
   * If you are asked to choose, pick the option for deploying from a GitHub repository.
3. Fill in the form:
   * **Repository**: `your-github-name/pattern-finder`
   * **Branch**: `main`
   * **Main file path**: `streamlit_app.py`
   * **App URL**: you can type a name you like, for example `my-pattern-finder`.
4. Click **Deploy**.
5. Wait while it installs everything. The first time takes a few minutes.
6. When it finishes, you will see the app with an Apple chart.

Copy the web address from your browser's address bar. It will look like `https://my-pattern-finder.streamlit.app`.

---

## Part 2: Add it to your iPhone home screen

1. On your iPhone, open **Safari** and go to your app's web address.
2. Tap the **Share** button (the square with an arrow pointing up).
3. Scroll down and tap **Add to Home Screen**.
4. Name it **Pattern Finder** and tap **Add**.

The app is now on your home screen.

---

## Using it on the phone

* **Chart tab**
  * Type a ticker and tap **Analyze**.
  * Pick a pattern from the list. The chart zooms to it and shows three lines: **Entry** (blue dotted), **Target** (green dashed) and **Stop** (red dashed).
  * Below the chart, the app explains the pattern in plain English.
  * Drag the chart sideways to move around. The **Zoom** buttons (3M, 6M, 1Y, All) change how much history you see.
* **Scan tab**: checks a list of tickers and shows which ones have active patterns.
* **Guide tab**: explains every pattern and every word the app uses.
* **Settings** (the gear at the top): change the period, bar size, sensitivity and which indicator panels to show.

---

## Good to know

* **It may need to "wake up".** Free Streamlit apps go to sleep when nobody has used them for a while. If you see a message saying the app is asleep, tap the button to wake it. It takes about a minute, then works normally.
* **Who can see it.** Anyone who has the web address can open it, unless you limit access in the app's settings on share.streamlit.io. There is nothing personal in it, but keep the address to yourself if you prefer.
* **If downloads fail.** Yahoo Finance sometimes blocks or limits downloads from cloud servers. Downloads are kept for 15 minutes to reduce how many requests the app makes.
  * If you see download errors for every ticker, wait a while and try again.
  * If it keeps happening, let me know and we can switch to another free price source.
  * Meanwhile, you can load a CSV price file in **Settings**.
* **Making changes later.** Edit or replace a file on GitHub, and the app updates itself within a minute or two.

---

## Optional: try it on your PC first

Double-click **Run_On_My_PC.bat**. The first time, it installs what it needs. Then the app opens in your web browser.

While that black window stays open, your iPhone can also use the app if it is on the **same Wi-Fi**:

1. Look in the black window for the line that starts with **Network URL**.
2. Type that address into Safari on your iPhone.

If Windows asks whether to allow access, choose **Private networks** and click **Allow**.

---

## Files

| File | What it is |
|---|---|
| `streamlit_app.py` | The phone screens: chart, scanner and guide. |
| `patterns.py` | The pattern-finding math. This is the same file as in the Windows app. |
| `indicators.py`, `data.py`, `report.py`, `pattern_info.py` | Indicators, data download and the plain-English text. These are shared with the Windows app. |
| `requirements.txt` | The list of libraries Streamlit installs. |
| `example_prices.csv` | Made-up practice data. |
| `Run_On_My_PC.bat` | Optional: runs the app on your PC. |
| `tests/test_patterns.py` | A self-test for the 19 patterns. |
