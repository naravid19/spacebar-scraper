<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->

<a id="readme-top"></a>

<!-- PROJECT SHIELDS -->

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Unlicense License][license-shield]][license-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/naravid19/spacebar-scraper">
    <h3 align="center">Spacebar News Scraper</h3>
  </a>

  <p align="center">
    โปรแกรมดึงข่าวอัตโนมัติจากเว็บไซต์ Spacebar.th พร้อม GUI ที่สวยงามและใช้งานง่าย
    <br />
    <a href="https://github.com/naravid19/spacebar-scraper"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/naravid19/spacebar-scraper">View Demo</a>
    &middot;
    <a href="https://github.com/naravid19/spacebar-scraper/issues">Report Bug</a>
    &middot;
    <a href="https://github.com/naravid19/spacebar-scraper/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->

## About The Project

**Spacebar News Scraper** คือโปรแกรม Desktop Application สำหรับดึงข้อมูลข่าวสารจากเว็บไซต์ [Spacebar.th](https://spacebar.th) พัฒนาด้วยภาษา Python โดยเน้นที่ความง่ายในการใช้งาน ความสวยงามของหน้าตาโปรแกรม (UI) และความเสถียรในการทำงาน

**ฟีเจอร์เด่น:**

- 🎨 **Modern UI**: ออกแบบด้วย Material Design (ใช้ `ttkbootstrap`) สวยงาม ทันสมัย และรองรับ Dark Mode
- 📂 **Customizable**: เลือกหมวดหมู่ข่าว (การเมือง, ธุรกิจ, สังคม ฯลฯ) และกำหนดช่วงหน้า (Page Range) ที่ต้องการดึงได้
- ⚡ **Robust**: ระบบจัดการ URL ที่แม่นยำ ป้องกัน Link เสีย และมีระบบ Retry อัตโนมัติเมื่อเน็ตมีปัญหา
- 📝 **Export Data**: บันทึกข้อมูลที่ได้เป็นไฟล์ CSV พร้อมเปิดนำไปใช้งานต่อได้ทันที

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

- [![Python][Python-badge]][Python-url]
- [![BeautifulSoup][BeautifulSoup-badge]][BeautifulSoup-url]
- [![Pandas][Pandas-badge]][Pandas-url]
- [![Tkinter][Tkinter-badge]][Tkinter-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->

## Getting Started

ทำตามขั้นตอนด้านล่างเพื่อติดตั้งและใช้งานโปรแกรมในเครื่องของคุณ

### Prerequisites

โปรแกรมนี้ต้องการ **Python 3.8** ขึ้นไป

- ตรวจสอบ version python:
  ```sh
  python --version
  ```

### Installation

1. Clone repo นี้ลงในเครื่อง
   ```sh
   git clone https://github.com/naravid19/spacebar-scraper.git
   ```
2. เข้าไปที่โฟลเดอร์โปรเจกต์
   ```sh
   cd spacebar-scraper
   ```
3. (Optional) สร้าง Virtual Environment
   ```sh
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   venv\Scripts\activate     # Windows
   ```
4. ติดตั้ง Libraries ที่จำเป็น
   ```sh
   pip install -r requirements.txt
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->

## Usage

1. รันโปรแกรมผ่านคำสั่ง:
   ```sh
   python spacebar_scraper_gui.py
   ```
2. หน้าต่างโปรแกรมจะเปิดขึ้นมา:
   - **หมวดหมู่ข่าว**: เลือกหมวดที่ต้องการ (เช่น การเมือง, ธุรกิจ)
   - **เริ่มหน้า / ถึงหน้า**: ระบุหน้าที่ต้องการให้เริ่มดึง และหน้าที่ให้หยุด (ใส่ 0 ถ้าต้องการดึงจนหมด)
   - **บันทึกไฟล์**: เลือกชื่อไฟล์และที่เก็บไฟล์ CSV
3. กดปุ่ม **START SCRAPING** เพื่อเริ่มทำงาน 🚀
4. รอจนกว่าจะเสร็จ (จะมีแถบความคืบหน้าแจ้งเตือน) เมื่อเสร็จแล้วสามารถกด **Open Folder** เพื่อดูไฟล์ผลลัพธ์ได้ทันที

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->

## Roadmap

- [x] GUI Fundamental Features (Category, Page Selection)
- [x] Export to CSV
- [x] Dark Mode Support
- [x] Professional Refactor (Type checking, Error Handling)
- [ ] Export to Excel (.xlsx) direct support
- [ ] Multi-threading for faster scraping (Parallel Requests)

See the [open issues](https://github.com/naravid19/spacebar-scraper/issues) for a full list of proposed features.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->

## License

Distributed under the Unlicense License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->

## Contact

Narawit - [@naravid19](https://github.com/naravid19)

Project Link: [https://github.com/naravid19/spacebar-scraper](https://github.com/naravid19/spacebar-scraper)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->

[contributors-shield]: https://img.shields.io/github/contributors/naravid19/spacebar-scraper.svg?style=for-the-badge
[contributors-url]: https://github.com/naravid19/spacebar-scraper/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/naravid19/spacebar-scraper.svg?style=for-the-badge
[forks-url]: https://github.com/naravid19/spacebar-scraper/network/members
[stars-shield]: https://img.shields.io/github/stars/naravid19/spacebar-scraper.svg?style=for-the-badge
[stars-url]: https://github.com/naravid19/spacebar-scraper/stargazers
[issues-shield]: https://img.shields.io/github/issues/naravid19/spacebar-scraper.svg?style=for-the-badge
[issues-url]: https://github.com/naravid19/spacebar-scraper/issues
[license-shield]: https://img.shields.io/github/license/naravid19/spacebar-scraper.svg?style=for-the-badge
[license-url]: https://github.com/naravid19/spacebar-scraper/blob/master/LICENSE.txt
[Python-badge]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[BeautifulSoup-badge]: https://img.shields.io/badge/BeautifulSoup-4.x-green?style=for-the-badge
[BeautifulSoup-url]: https://www.crummy.com/software/BeautifulSoup/
[Pandas-badge]: https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white
[Pandas-url]: https://pandas.pydata.org/
[Tkinter-badge]: https://img.shields.io/badge/Tkinter-GUI-blue?style=for-the-badge
[Tkinter-url]: https://docs.python.org/3/library/tkinter.html
