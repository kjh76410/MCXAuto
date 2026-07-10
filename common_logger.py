import time

def start_device_logging(d, log_console=None):
    """
    로그 앱을 다이렉트로 실행하여 Logcat과 Pcap을 껐다가 켭니다.
    화면 내에 버튼이 보이지 않으면 스와이프하여 찾고, 필요한 경우 팝업을 처리합니다.
    """
    def print_log(msg):
        print(msg)
        if log_console:
            log_console.insert("end", f"{msg}\n")
            log_console.see("end")

    # 💡 [업데이트] requires_ok 파라미터 추가! (True면 팝업에서 OK를 누름)
    def find_and_click_button(start_text, stop_text, button_name, requires_ok=False):
        max_scroll_attempts = 3  
        
        for attempt in range(max_scroll_attempts + 1):
            start_btn = d(textContains=start_text)
            stop_btn = d(textContains=stop_text)

            if stop_btn.exists:
                print_log(f"⚡ {button_name}이(가) 이미 실행 중입니다. 껐다가 다시 켭니다.")
                stop_btn.click()
                time.sleep(1.5) 
                
                if d(textContains=start_text).exists:
                    d(textContains=start_text).click()
                    print_log(f"🔄 {button_name} 시작 버튼 클릭!")
                    
                    # 💡 팝업 처리 로직
                    if requires_ok:
                        time.sleep(1.0) # 팝업이 뜰 때까지 살짝 대기
                        ok_btn = d(text="OK")
                        if not ok_btn.exists:
                            ok_btn = d(text="확인") # 한글일 경우 대비
                            
                        if ok_btn.exists:
                            ok_btn.click()
                            print_log(f"✅ {button_name} 팝업 'OK' 클릭 완료!")
                            time.sleep(0.5)
                        else:
                            print_log(f"⚠️ {button_name} 팝업 'OK' 버튼을 찾을 수 없습니다.")

                    print_log(f"✅ {button_name} 재시작 완료!")
                return True 

            elif start_btn.exists:
                start_btn.click()
                print_log(f"🔄 {button_name} 시작 버튼 클릭!")
                
                # 💡 팝업 처리 로직
                if requires_ok:
                    time.sleep(1.0) # 팝업이 뜰 때까지 살짝 대기
                    ok_btn = d(text="OK")
                    if not ok_btn.exists:
                        ok_btn = d(text="확인") # 한글일 경우 대비
                        
                    if ok_btn.exists:
                        ok_btn.click()
                        print_log(f"✅ {button_name} 팝업 'OK' 클릭 완료!")
                        time.sleep(0.5)
                    else:
                        print_log(f"⚠️ {button_name} 팝업 'OK' 버튼을 찾을 수 없습니다.")

                print_log(f"✅ {button_name} 시작 완료!")
                return True 
                
            else:
                if attempt < max_scroll_attempts:
                    print_log(f"🔍 화면에서 {button_name} 버튼을 찾는 중... (스크롤 {attempt+1})")
                    d.swipe(0.5, 0.8, 0.5, 0.2, 0.5)
                    time.sleep(1) 
        
        print_log(f"⚠️ {button_name} 버튼을 화면에서 찾을 수 없습니다.")
        return False


    print_log("\n[System] 공통 로그 수집 프로세스를 시작합니다.")

    try:
        print_log("📱 로그 앱(CtbLog)을 다이렉트로 실행합니다.")
        d.app_stop("com.ctb.log") 
        time.sleep(1)
        
        d.app_start("com.ctb.log", "com.ctb.log.CtbLog")
        time.sleep(2.0) 

        # (1) Logcat 찾아서 켜기 (얘는 팝업 없으니까 그냥 호출)
        find_and_click_button(start_text="LOGCAT START", stop_text="LOGCAT STOP", button_name="LOGCAT")
        
        time.sleep(0.5)

        # (2) Pcap 찾아서 켜기 (💡 얘는 팝업 있으니까 requires_ok=True 추가!)
        find_and_click_button(start_text="PCAP DUMP START", stop_text="PCAP DUMP STOP", button_name="PCAP DUMP", requires_ok=True)

        time.sleep(1)
        d.press("home")
        print_log("[System] 모든 로그 세팅을 마치고 바탕화면으로 복귀합니다.")

    except Exception as e:
        print_log(f"❌ 로그 앱 실행 중 오류 발생: {e}")