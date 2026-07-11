# PC Scraper

> [!NOTE] 
> This repository is for personal use. The code is designed and intended to run on a laptop with an Intel Atom N2600 processor, 4 GB of RAM, and a WiFi connection. The operating system used is Arch Linux without a desktop environment (headless) with the minimum packages required to have a functional distribution.

This repository contains two web scrapers that operate independently:
- ML web scraper 
- CG web scraper 

Both are used to scrape PC component prices, allowing me to make smart purchasing decisions by analyzing prices and using metrics to detect discounts or atypically low prices.

> [!IMPORTANT] 
> Both scraping scripts must be used in compliance with the terms and conditions of the websites involved. Limit your query volume and use them wisely; the author is not responsible for blocked accounts, banned IPs, or any issues arising from the misuse of these scripts.

Read the instructions in Spanish [here](README_ES.md).

## How It Works

The scrapers are located in the following directories:
- ml_scraper 
- cg_scraper

Each scraper performs its task differently. `cg_scraper` uses `requests` since it has direct access to the API. On the other hand, `ml_scraper` uses Playwright to achieve the same result as a real web browser, parsing the HTML and extracting relevant data for subsequent storage and statistical analysis.

### cg_scraper 

This directory contains multiple Python files and a Bash script. The file named `cg_scraper.py` accesses the CG API using the `requests` library and retrieves a JSON of products, which it then processes to filter out the items to be saved. Additionally, it computes basic statistics on daily prices, allowing the generation of a graphical report using the `graph_data.py` script. This latter script works independently and uses the data stored in the database to generate a price-over-time chart using box plots (mean, standard deviation, maximum, and minimum).

The `run_cg_scraper.sh` file is a Bash script that essentially performs 3 tasks:
1. Verifies the internet or local network connection based on the configuration.
2. Runs the scraping script.
3. Sends the scraping results via email.

The first step is crucial because the setup is designed to run unattended on devices with a WiFi connection. If the internet connection is interrupted or inactive, the script will execute as soon as the connection is restored.

The `json2html.py` file works in conjunction with `run_cg_scraper.sh`, converting the extracted database data into an HTML table with general statistics. This table is then emailed according to the configuration.

### ml_scraper 

The general operation is very similar to `cg_scraper`. There is an `ml_scraper.py` file responsible for scraping, but using Playwright in this case. The `db.py` file creates the database where products are stored daily. This latter file works automatically alongside `ml_scraper.py`, so there is no need to execute it manually.

Just like in `cg_scraper`, the Bash script `run_ml_scraper.sh` performs the same tasks but focuses on scraping a different type of components. They are separate scripts because you might want to run one more frequently than the other throughout the day. For instance, you could run `run_cg_scraper.sh` three times a day and `run_ml_scraper.sh` only once. Similarly, `ml_mail_report.sh` prepares the data to be sent via email as a table.

> [!IMPORTANT] 
> For the bash scripts to work properly, create a rule in /etc/sudoers.d/rulename to allow your user execute the necesary commands without password. You can follow the example below:
```sh 
username ALL=(ALL) NOPASSWD: /usr/bin/ip link set wlp2s0 down, /usr/bin/ip link set wlp2s0 up
```

### Testing

If you are testing your most basic configuration, use the `ml_scraper.py` and `cg_scraper.py` scripts to execute the scraping task and verify if the result is as expected before deploying the fully automated server.

## Automated Deployment

The automated deployment aims to execute the scraping scripts on a scheduled basis. This task is handled using systemd (via the configuration files provided in this repository), although you can use any task scheduler like cron, which you would have to configure manually.

To establish the prerequisites for automated deployment, you must use a machine running Linux, with systemd and Python installed. Specifically, this configuration has been developed and tested on Arch Linux, but it can work on other distributions that use systemd and have a similar setup.

To begin, you must configure systemd on your operating system. The `config_env.sh` script contains the configuration for the systemd units (timers and services) responsible for periodically repeating the scraping task. Before running this script to configure your system and systemd tasks, use the `env.config.example` file as a template to create your `env.config` file, which will contain the directories and file names used by systemd and the scraping scripts. After creating the `env.config` file, you must configure the `msmtp` email client with an account so that the daily report emails can be sent successfully. If you do not wish to receive emails, you can skip this step. You will also need to comment out or delete the lines associated with sending emails in the `ml_scraper/run_ml_scraper.sh` and `cg_scraper/run_cg_scraper.sh` scripts. 

Once the above steps are completed, you can execute `config_env.sh`, which will create the timers (analogous to cron jobs) using systemd. With this, the automated deployment is fully configured.

## License

This repository is licensed under the MIT License.
