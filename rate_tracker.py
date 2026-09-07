import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

TARGETS_FILE = "targets.csv"
OUTPUT_FILE = "competition_rate_log.csv"

def load_target_list():
    if not os.path.exists(TARGETS_FILE):
        print(f"❌ '{TARGETS_FILE}' 파일을 찾을 수 없습니다.")
        return []
    try:
        try:
            df = pd.read_csv(TARGETS_FILE, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(TARGETS_FILE, encoding='euc-kr')
        return df.to_dict('records')
    except Exception as e:
        print(f"❌ 파일 읽기 오류: {e}")
        return []

def fetch_competition_data(target):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        response = requests.get(target["url"], headers=headers, timeout=10)
        response.encoding = response.apparent_encoding if response.apparent_encoding else 'utf-8'
        
        if response.status_code != 200:
            print(f"❌ 접속 에러 ({response.status_code}): {target['univ_name']}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # A. 진학어플라이 (jinhak)
        if str(target.get("site_type")).strip().lower() == "jinhak":
            h2_tags = soup.find_all(['h2', 'h3', 'h4', 'caption'])
            target_div = None
            for tag in h2_tags:
                if str(target["target_group"]) in tag.text:
                    target_div = tag.find_parent('div')
                    break
            if not target_div:
                target_div = soup.find(lambda e: e.name in ['div', 'tr', 'td'] and str(target["target_group"]) in e.text)

            if target_div:
                table = target_div.find('table') or target_div.find_next('table')
                if table:
                    for row in table.find_all('tr'):
                        row_text = row.text.strip()
                        if str(target["target_dept"]) in row_text:
                            cols = [td.text.strip() for td in row.find_all(['td', 'th']) if td.text.strip()]
                            for i, text in enumerate(cols):
                                if str(target["target_dept"]) in text:
                                    return {
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "univ_name": target["univ_name"],
                                        "group_name": target["target_group"],
                                        "dept_name": text,
                                        "quota": cols[i + 1] if i + 1 < len(cols) else "-",
                                        "applied": cols[i + 2] if i + 2 < len(cols) else "-",
                                        "ratio": cols[i + 3] if i + 3 < len(cols) else "-"
                                    }

        # B. 유웨이어플라이 (uway)
        else:
            for table in soup.find_all('table'):
                parent_text = table.parent.text if table.parent else ""
                prev_elem = table.find_previous(['h1','h2','h3','h4','h5','div','caption'])
                prev_text = prev_elem.text if prev_elem else ""
                
                t_group = str(target["target_group"])
                t_dept = str(target["target_dept"])

                if t_group in parent_text or t_group in prev_text or t_group in table.text:
                    for row in table.find_all('tr'):
                        if t_dept in row.text.strip():
                            cols = [td.text.strip() for td in row.find_all(['td', 'th']) if td.text.strip()]
                            for i, text in enumerate(cols):
                                if t_dept in text:
                                    return {
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "univ_name": target["univ_name"],
                                        "group_name": target["target_group"],
                                        "dept_name": text,
                                        "quota": cols[i + 1] if i + 1 < len(cols) else "-",
                                        "applied": cols[i + 2] if i + 2 < len(cols) else "-",
                                        "ratio": cols[i + 3] if i + 3 < len(cols) else "-"
                                    }
        return None
    except Exception as e:
        print(f"❌ 크롤링 실패 ({target['univ_name']}): {e}")
        return None

def main():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"⏱️ [{now_str}] 지원현황 수집 중...")
    
    target_list = load_target_list()
    if not target_list:
        return

    collected_data = []
    for target in target_list:
        data = fetch_competition_data(target)
        if data:
            collected_data.append(data)
            print(f"  ▶ [{data['univ_name']}] {data['group_name']} - {data['dept_name']} | 지원: {data['applied']}명")

    if collected_data:
        df = pd.DataFrame(collected_data)
        file_exists = os.path.exists(OUTPUT_FILE)
        df.to_csv(OUTPUT_FILE, mode='a', index=False, header=not file_exists, encoding='utf-8-sig')
        print(f"✅ 수집 완료!")

if __name__ == "__main__":
    main()