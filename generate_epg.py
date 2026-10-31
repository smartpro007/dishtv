import json
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import urllib3
import gzip
import os

urllib3.disable_warnings()

# १. DishTV Signin करून Token मिळवणे
def get_auth_token():
    try:
        resp = urllib3.request(
            "POST",
            "https://www.dishtv.in/services/epg/signin",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.dishtv.in/channel-guide.html"
            }
        )
        data = resp.json()
        return data.get('token')
    except Exception as e:
        print(f"Error fetching token: {e}")
        return None

def main():
    token = get_auth_token()
    if not token:
        print("Failed to get token. Exiting.")
        return

    root = ET.Element('tv')
    root.set('generator-info-url', 'https://github.com')

    # दिनांक मर्यादा: मागील ८ दिवस ते पुढील २ दिवस (एकूण ११ दिवस)
    today = datetime.now()
    dates_to_fetch = [(today + timedelta(days=i)).strftime("%d/%m/%Y") for i in range(-8, 3)]

    print(f"Fetching EPG for {len(dates_to_fetch)} days...")

    # पिलं पेज फेच करून टोटल पेजेस किंवा चॅनेल्स मिळवू
    # (इथे आपण सर्व 107 पेजेस लूप करू शकतो किंवा आवश्यक चॅनेल्स घेऊ शकतो)
    total_pages = 107  # जसे आपण मगाशी पाहिले
    
    channels_dict = {}

    for date_str in dates_to_fetch:
        print(f"Processing date: {date_str}")
        for page in range(1, total_pages + 1):
            body_data = json.dumps({
                "channelgenre": "",
                "language": "",
                "allowPastEvents": "true",
                "dataSize": "large",
                "pageNum": page,
                "date": date_str
            })

            try:
                resp = urllib3.request(
                    "POST",
                    f"https://www.dishtv.in/services/epg/channels?pageNum={page}&date={date_str}",
                    body=body_data,
                    headers={
                        "Authorization-Token": token,
                        "Content-Type": "application/json",
                        "Origin": "https://www.dishtv.in",
                        "Referer": "https://www.dishtv.in/channel-guide.html",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    }
                )
                
                res_json = resp.json()
                program_details = res_json.get('programDetailsByChannel', [])
                
                if not program_details:
                    break

                for j in program_details:
                    epgid = str(j['channelid'])
                    
                    # चॅनेल माहिती एकदाच रूढ करा
                    if epgid not in channels_dict:
                        channels_dict[epgid] = {
                            "name": j['channelname'],
                            "image": j.get('channelimage', ''),
                            "lcn": j.get('lcn', '')
                        }

                    # चॅनेल टॅग XML मध्ये जोडणे (जर आधी नसेल तर)
                    # (किंवा थेट प्रोग्राम्स जोडणे)
                    for prg in j.get('programs', []):
                        start = prg.get('start', '').replace('-','').replace(':','').replace('T','').replace('Z',' +0530')
                        stop = prg.get('stop', '').replace('-','').replace(':','').replace('T','').replace('Z',' +0530')
                        
                        prog_elem = ET.SubElement(root, 'programme')
                        prog_elem.set('channel', epgid)
                        prog_elem.set('start', start)
                        prog_elem.set('stop', stop)

                        title = ET.SubElement(prog_elem, 'title')
                        title.text = prg.get('title', '')

                        desc = ET.SubElement(prog_elem, 'desc')
                        desc.text = prg.get('desc', '')

                        cat = ET.SubElement(prog_elem, 'category')
                        cat.text = prg.get('genre', '')

                        ico = ET.SubElement(prog_elem, 'icon')
                        ico.set('src', prg.get('programmeurl', ''))

            except Exception as e:
                # पेज फेच एरर आल्यास पुढे जाणे
                continue

    # चॅनेल टॅग्ज शेवटी किंवा सुरुवातीला ॲड करणे
    for epgid, info in channels_dict.items():
        chnl = ET.Element('channel', {'id': epgid})
        dspl = ET.SubElement(chnl, 'display-name')
        dspl.text = info['name']
        if info['image']:
            icon = ET.SubElement(chnl, 'icon')
            icon.set('src', info['image'])
        if info['lcn']:
            lcn = ET.SubElement(chnl, 'lcn')
            lcn.text = info['lcn']
        root.insert(0, chnl) # रूढ रूटच्या वर चॅनेल टाकणे

    # फाईल फोल्डर तयार करणे
    os.makedirs('./epg', exist_ok=True)
    xml_data = ET.tostring(root, encoding='utf-8', xml_declaration=True)

    with open('./epg/dishtv.xml', 'wb') as f:
        f.write(xml_data)
    
    with gzip.open('./epg/dishtv.xml.gz', 'wb') as f:
        f.write(xml_data)
    
    print("EPG generated and compressed successfully!")

if __name__ == '__main__':
    main()
          
