import csv
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from config import START_URL, HEADLESS, MAX_ITEMS, OUTPUT_CSV


def build_driver():
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,900")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def clean_price(text: str) -> str:
    if not text:
        return ""
    t = str(text).strip()
    # 只保留最核心的 1,380円
    m = re.search(r"(\d[\d,]*)\s*円", t)
    return f"{m.group(1)}円" if m else ""


def clean_rating(text: str) -> str:
    if not text:
        return ""
    t = str(text).strip()
    # span.score 通常就是 4.38 这种
    m = re.search(r"(\d\.\d{1,2})", t)
    return m.group(1) if m else ""


def main():
    driver = build_driver()
    try:
        driver.get(START_URL)
        wait = WebDriverWait(driver, 20)

        # 等结果区出现
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.searchResults")))

        # ✅ 标题链接（你的 selector 泛化版）
        # 这里抓到的是每个商品的标题 a
        title_links = driver.find_elements(By.CSS_SELECTOR, "div.searchResults div[class*='title'] h2 > a")

        rows = []
        for a in title_links:
            if len(rows) >= MAX_ITEMS:
                break

            url = a.get_attribute("href") or ""
            # 只保留商品页链接
            if "item.rakuten.co.jp" not in url:
                continue

            name = (a.text or a.get_attribute("title") or a.get_attribute("aria-label") or "").strip()
            if not name:
                continue

            # ✅ 找到该 a 所在的“商品卡片”容器：往上找 searchresultitem / 其他可能容器
            try:
                card = a.find_element(
                    By.XPATH,
                    "./ancestor::div[contains(@class,'searchresultitem') or contains(@class,'rpp') or contains(@class,'dui-card')][1]"
                )
            except Exception:
                # 兜底：往上找第一个大 div
                card = a.find_element(By.XPATH, "./ancestor::div[1]")

            # ✅ 用你给的价格 selector（去掉 nth-child，改为在 card 内找）
            price = ""
            try:
                price_el = card.find_element(By.CSS_SELECTOR, "div[class*='price-wrapper'] > div")
                price = price_el.text.strip()
            except Exception:
                price = ""

            # ✅ 用你给的评分 selector（在 card 内找）
            rating = ""
            try:
                rating_el = card.find_element(By.CSS_SELECTOR, "div.content.review a span.score")
                rating = rating_el.text.strip()
            except Exception:
                rating = ""

            price = clean_price(price)
            rating = clean_rating(rating)

            rows.append({"name": name, "price": price, "rating": rating, "url": url})
            time.sleep(0.05)

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "price", "rating", "url"])
            writer.writeheader()
            writer.writerows(rows)

        print(f"Saved {len(rows)} rows -> {OUTPUT_CSV}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()