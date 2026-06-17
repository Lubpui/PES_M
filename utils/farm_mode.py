
from utils.utils_helper import loop_action_before_confirm, detect_multiple_colors, check_before_click, loop_back_to_home
import json
import os
import time
import queue as queue_module
import logging

logger = logging.getLogger(__name__)

def farm_mode(serial: str, ui_queue, **kwargs):
    # Extract helper functions from kwargs
    start_farm_mode = kwargs.get('start_farm_mode')
    loop_confirm_wait_for = kwargs.get('loop_confirm_wait_for')
    wait_for = kwargs.get('wait_for')
    tap_location = kwargs.get('tap_location')
    swipe_down = kwargs.get('swipe_down')
    esc_key = kwargs.get('esc_key')
    capture_screen = kwargs.get('capture_screen')
    extract_text_tesseract = kwargs.get('extract_text_tesseract')
    capture_gacha_screen = kwargs.get('capture_gacha_screen')
    loop_close_promo = kwargs.get('loop_close_promo')
    is_pes_visible = kwargs.get('is_pes_visible')
    open_pes = kwargs.get('open_pes')
    handle_move_file = kwargs.get('handle_move_file')
    scale_crop_area = kwargs.get('scale_crop_area')  # Add this
    
    # Get update_stage function from kwargs (for saving progress)
    update_stage_func = kwargs.get('update_stage')
    
    # Get workflow and device config loaders
    get_workflow = kwargs.get('get_workflow')
    get_current_stage = kwargs.get('get_current_stage')
    
    # Get main_configs from kwargs
    main_configs = kwargs.get('main_configs', {})

    # ================================
    # Safe Queue Wrapper with Timeout
    # ================================
    def safe_ui_queue_put(data, timeout=5.0):
        """Wrapper around ui_queue.put with timeout to prevent deadlock"""
        try:
            ui_queue.put(data, timeout=timeout)
        except queue_module.Full:
            logger.warning(f"UI Queue full for {serial}, data dropped: {data}")
        except Exception as e:
            logger.error(f"Error putting data in UI queue for {serial}: {e}")

        # Load workflow and get current stage from device config
    workflow = get_workflow() if get_workflow else []
    current_stage = get_current_stage(serial) if get_current_stage else 1

    is_first_run = True

    def loop_check_color():        
        crop_area = (904, 89, 922, 114)
        # Scale crop area for device resolution
        scaled_crop_area = scale_crop_area(crop_area) if scale_crop_area else crop_area
        
        # ตั้งค่าสี
        white_hsv_lower = (0, 0, 200)
        white_hsv_upper = (180, 50, 255)
        
        green_hsv_lower = (35, 50, 50)
        green_hsv_upper = (85, 255, 255)
        
        gray_green_hsv_lower = (45, 20, 130)
        gray_green_hsv_upper = (100, 60, 200)
        
        gray_dark_hsv_lower = (0, 0, 30)
        gray_dark_hsv_upper = (180, 30, 60)
        
        found_color = None
        loop_count = 0
        max_loops = 100
        
        while loop_count < max_loops:
            loop_count += 1
            
            # Capture screen
            screen_path = capture_screen(serial)
            
            # ตรวจจับหลายสี
            all_colors = detect_multiple_colors(
                image_path=screen_path,
                color_ranges={
                    'white': (white_hsv_lower, white_hsv_upper),
                    'green': (green_hsv_lower, green_hsv_upper),
                    'gray_green': (gray_green_hsv_lower, gray_green_hsv_upper),
                    'gray_dark': (gray_dark_hsv_lower, gray_dark_hsv_upper),
                },
                crop_area=scaled_crop_area,
                min_area=10,
                color_space='HSV'
            )
            
            # Filter และ print ผลลัพธ์
            valid_colors = {}
            
            for color_name, results in all_colors.items():
                if len(results) > 0:
                    valid_colors[color_name] = results
            
            # เช็ค combination ของสี
            has_white = 'white' in valid_colors and len(valid_colors['white']) > 0
            has_green = 'green' in valid_colors and len(valid_colors['green']) > 0
            has_gray_green = 'gray_green' in valid_colors and len(valid_colors['gray_green']) > 0
            has_gray_dark = 'gray_dark' in valid_colors and len(valid_colors['gray_dark']) > 0
            
            # Logic ตามที่ต้องการ
            if (has_gray_green and has_gray_dark) or has_gray_dark:
                tap_location(serial, 911, 107)
                time.sleep(1)
                found_color = 'gray_dark'
                # วนไปอีกรอบ
                continue
            
            elif has_green and has_white:
                found_color = 'green_white'
                break
            
            else:
                print("✗ No matching color combination found → Retrying...")
                time.sleep(1)
                continue
        
        print(f"\n=== LOOP COMPLETED ===")
        print(f"Final result: {found_color}")
        print(f"Total loops: {loop_count}")

    def swipe_to_event():
        is_event = False
        def set_event():
            nonlocal is_event
            is_event = True

        while True:

            wait_for(
                serial=serial,
                detection_type='text',
                target_file='event', 
                text_action=lambda:[
                    tap_location(serial, 182, 255),
                    set_event(),
                ],
                text_crop_area=(82, 312, 160, 342),
                extract_mode = 'normal',
                is_loop=False
            )

            if is_event:
                break
        
            swip_start = (348, 267)
            swip_end = (96, 271)

            swipe_down(serial, swip_start[0],swip_start[1], swip_end[0], swip_end[1], duration_ms=3000)
            swipe_down(serial, swip_end[0], swip_end[1], swip_end[0], 300, duration_ms=1000)
            time.sleep(2)

    def initial_stage_1():
        loop_confirm_wait_for(
            target_file='contract',
            text_action=lambda:[
                tap_location(serial, 132, 458),
            ],
            text_crop_area=(438, 497, 520, 520),
        )

        loop_action_before_confirm(
            serial=serial,
            action_function=lambda: tap_location(serial, 473, 473),
            target_file='mode',
            text_crop_area=(415, 490, 480, 522),
            wait_for=wait_for
        )

        swipe_to_event()

        loop_confirm_wait_for(
            target_file='event', # Evnet
            text_action=lambda:[
                tap_location(serial, 342, 267)
            ],
            text_crop_area=(500, 310, 570, 343),
        )

    def pre_stage():
        nonlocal is_first_run
        is_visible = is_pes_visible(serial)

        if not is_visible or is_first_run:
            open_pes()
            
            if not is_first_run:
                safe_ui_queue_put(('substage', serial, 'มันหลุดอะแต่กลับมาแล้ว'))
                loop_confirm_wait_for(
                    target_file='konam', # Konami
                    text_action=lambda:[
                        tap_location(serial, 617, 356), # กดเริ่มต้นหน้าหลัก
                    ],
                    text_crop_area=(628, 480, 688, 507), # พื้นที่คำว่า Konami
                )

                loop_close_promo()

            if current_stage == 1:
                safe_ui_queue_put(('substage', serial, 'กลับเข้า stage 1'))
                initial_stage_1()

    def loop_farm_ai():
        nonlocal is_first_run
        is_first_haft = True
        loop_count = 1

        while True:
            is_break = False
            def set_break():
                nonlocal is_break
                is_break = True
            
            wait_for(
                serial=serial,
                detection_type='text',
                target_file='game', 
                text_action=lambda:[
                    wait_for(
                        serial=serial,
                        detection_type='text',
                        target_file='100gp', 
                        text_action=lambda:[
                            set_break()
                        ],
                        text_crop_area=(606, 266, 722, 314),
                        extract_mode = 'name',
                        is_loop=False,
                        is_ignore_x=True
                    )
                ],
                text_crop_area=(120, 86, 217, 111),
                extract_mode = 'name'
            )

            if is_break:
                esc_key(serial)
                break

            if loop_count == 1:
                loop_confirm_wait_for(
                    target_file='game', # game plan
                    text_action=lambda:[
                        tap_location(serial, 217, 111), # กด Game Plan
                    ],
                    text_crop_area=(120, 86, 217, 111),
                )

                safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 1'))
                loop_confirm_wait_for(
                    target_file='game',
                    text_action=lambda:[
                        tap_location(serial, 869, 418), 
                        tap_location(serial, 478, 358), 
                    ],
                    text_crop_area=(724, 11, 774, 34),
                )

                safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 2'))
                wait_for(
                    serial=serial,
                    detection_type='text',
                    target_file='player', 
                    text_action=lambda:[
                        tap_location(serial, 474, 103) # กด By stats
                    ],
                    text_crop_area=(382, 20, 579, 54),
                    extract_mode = 'name',
                    pre_action=lambda:[
                        tap_location(serial, 1161, 556, is_ignore_x=True) # กด player
                    ]
                )

                safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 3'))
                loop_confirm_wait_for(
                    target_file='player',
                    text_action=lambda:[
                        tap_location(serial, 599, 344), # กด Auto pick
                    ],
                    text_crop_area=(381, 176, 709, 206), # พื้นที่คำว่า Players Have Been Locked
                )

                safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 5'))
                loop_confirm_wait_for(
                    target_file='game',
                    text_action=lambda:[
                        esc_key(serial), 
                    ],
                    text_crop_area=(724, 11, 774, 34), # พื้นที่คำว่า Players Have Been Locked
                )

                safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 5.1'))
                loop_confirm_wait_for(
                    target_file='game', # game plan
                    text_action=lambda:[
                        tap_location(serial, 138, 308), # กด Match Settings
                    ],
                    text_crop_area=(120, 86, 217, 111),
                )

                safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 5.2'))
                wait_for(
                    serial=serial,
                    detection_type='text',
                    target_file='match', 
                    text_action=lambda:[
                        tap_location(serial, 117, 155) # กด By stats
                    ],
                    text_crop_area=(48, 125, 117, 155),
                    extract_mode = 'name'
                )

                safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 5.3'))
                loop_confirm_wait_for(
                    target_file='match', # game plan
                    text_action=lambda:[
                        swipe_down(serial, 474, 378, 474, 340, duration_ms=1000),
                        time.sleep(1),
                        tap_location(serial, 460, 300), # กด Superstar
                        tap_location(serial, 477, 477), # กด Superstar
                    ],
                    text_crop_area=(413, 21, 484, 51),
                )

                safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 5.4'))
                loop_confirm_wait_for(
                    target_file='match',
                    text_action=lambda:[
                        esc_key(serial),
                    ],
                    text_crop_area=(48, 125, 117, 155),
                )

            safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 6'))
            loop_confirm_wait_for(
                target_file='game', # game plan
                text_action=lambda:[
                    tap_location(serial, 863, 507), # กด To Match
                ],
                text_crop_area=(120, 86, 217, 111),
            )

            safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 7'))
            loop_confirm_wait_for(
                target_file='next', # game plan
                text_action=lambda:[
                    tap_location(serial, 863, 507), # กด To Next
                ],
                text_crop_area=(840, 491, 897, 522),
            )
            
            safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 8'))
            loop_confirm_wait_for(
                target_file='game',
                text_action=lambda:[
                    tap_location(serial, 863, 507), # กด To Match
                ],
                text_crop_area=(724, 11, 774, 34),
            )

            safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 9'))
            loop_action_before_confirm(
                serial=serial,
                action_function=lambda: tap_location(serial, 913, 34),
                target_file='game',
                text_crop_area=(118, 239, 217, 268),
                wait_for=wait_for
            )

            safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 10'))
            if is_first_run:
                tap_location(serial, 153, 388)

                wait_for(
                    serial=serial,
                    detection_type='text',
                    target_file='contro', 
                    text_action=lambda:[
                        tap_location(serial, 182, 275) # กด By stats
                    ],
                    text_crop_area=(47, 237, 182, 275),
                    extract_mode = 'name'
                )

                loop_confirm_wait_for(
                    target_file='contro',
                    text_action=lambda:[
                        tap_location(serial, 444, 164), # กด To Match
                        tap_location(serial, 480, 480), # กด To Match
                    ],
                    text_crop_area=(411, 21, 548, 53), # พื้นที่คำว่า Players Have Been Locked
                )

                time.sleep(1)

                esc_key(serial)

                time.sleep(2)

                is_first_run = False
            
            esc_key(serial)

            safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 11'))
            loop_check_color()

            safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 12'))
            loop_action_before_confirm(
                serial=serial,
                action_function=lambda: [
                    check_before_click(
                        serial=serial,
                        action_function=lambda: [
                            tap_location(serial, 480, 340),
                            tap_location(serial, 480, 360),
                            tap_location(serial, 480, 380),
                            tap_location(serial, 480, 400),
                            tap_location(serial, 480, 420),
                            tap_location(serial, 480, 440),
                            tap_location(serial, 480, 460),
                            tap_location(serial, 480, 480),
                        ],
                        target_file='age',
                        text_crop_area=(591, 170, 664, 219),
                        action_target=lambda: [
                            esc_key(serial),
                            time.sleep(2),
                            esc_key(serial),
                            time.sleep(2),
                            tap_location(serial, 881, 516),
                        ],
                        is_ignore_x=True,
                        wait_for=wait_for
                    ),
                    check_before_click(
                        serial=serial,
                        action_function=lambda: tap_location(serial, 881, 516), # กด To Next
                        target_file='match',
                        text_crop_area=(796, 492, 896, 524),
                        wait_for=wait_for
                    ),
                    
                ], # กด skip
                target_file='match',
                text_crop_area=(796, 492, 896, 524),
                last_action_function=lambda: [],
                wait_for=wait_for
            )

            safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 13'))
            wait_for(
                serial=serial,
                detection_type='text',
                target_file='match', 
                text_action=lambda:[
                    tap_location(serial, 480, 340),
                    tap_location(serial, 480, 360),
                    tap_location(serial, 480, 380),
                    tap_location(serial, 480, 400),
                    tap_location(serial, 480, 420),
                    tap_location(serial, 480, 440),
                    tap_location(serial, 480, 460),
                    tap_location(serial, 480, 480),
                ],
                text_crop_area=(796, 492, 896, 524),
                extract_mode = 'name'
            )

            # safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: 13'))
            # loop_action_before_confirm(
            #     serial=serial,
            #     action_function=lambda: tap_location(serial, 477, 400), # กด skip
            #     target_file='match',
            #     text_crop_area=(400, 338, 470, 370),
            #     last_action_function=lambda: tap_location(serial, 724, 28), # กด To Missions
            #     wait_for=wait_for
            # )

            loop_count += 1

            # reward_count = ''
        
            # def reward_detection(serial):
            #     nonlocal reward_count
            #     from collections import Counter
                
            #     while True:
            #         coin_list = []
                    
            #         # เช็ค 3 ครั้ง
            #         for _ in range(3):
            #             screen_path = capture_screen(serial)
            #             text_crop_area = (778, 152, 808, 181) # พื้นที่คำว่า reward count
            #             extract_mode = 'number'

            #             tesseract_result = extract_text_tesseract(serial, ui_queue, screen_path, text_crop_area, extract_mode)
            #             if 'error' in tesseract_result:
            #                 print('❌')
            #                 coin_value = ''
            #             else:
            #                 coin_value = tesseract_result['original'].replace(' ', '').replace('\n', '').lower()
                        
            #             coin_list.append(coin_value)
            #             time.sleep(0.5)  # เพิ่มเวลารอระหว่างเช็ก
                    
            #         # ตรวจสอบว่า 3 ตัวต่างกันหมด
            #         if len(set(coin_list)) == 3:
            #             # ถ้าทั้ง 3 ตัวต่างกันหมด ให้วนทำใหม่
            #             print(f"ค่า coin ไม่ตรงกัน: {coin_list} วนทำใหม่")
            #             continue
                    
            #         # เอาค่าที่มีมากที่สุด
            #         counter = Counter(coin_list)
            #         reward_count = counter.most_common(1)[0][0]
            #         print(f"ค่า coin: {coin_list} → ผลลัพธ์: {reward_count}")
            #         break

            # safe_ui_queue_put(('substage', serial, 'ฟาร์ม AI: เช็ค mission'))
            # wait_for(
            #     serial=serial,
            #     detection_type='text',
            #     target_file='detail', 
            #     text_action=lambda:[
            #         reward_detection(serial),
            #     ], 
            #     text_crop_area=(442, 491, 518, 522),
            #     extract_mode='name'
            # )

            # esc_key(serial)

            # if reward_count == '0':
            #     handle_move_file(current_file, current_folder, [], num_name, mode='farm', accumulat=accumulat)
            #     break

    def stage_1():
        # ดึง match_slot_list จาก config
        match_slot_list = main_configs.get('match_slot_list', []) if main_configs.get('match_slot_list') else None
        count_match = len(match_slot_list) if match_slot_list else 1  # default 1 ถ้าไม่มี list

        swip_start = (628, 252)
        swip_end = (90, 252)

        is_break = False
        def set_break():
            nonlocal is_break
            is_break = True

        def loop_check():

            is_break_loop_check = False
            def set_break_loop_check():
                nonlocal is_break_loop_check
                is_break_loop_check = True

            is_last_event = False
            def set_last_event():
                nonlocal is_last_event
                is_last_event = True
            
            while True:
                wait_for(
                    serial=serial,
                    detection_type='text',
                    target_file='con', 
                    sub_target_file='enter',
                    text_action=lambda:[set_break_loop_check(), set_last_event()], 
                    text_crop_area=(729, 391, 830, 429), # Nominating Contracts | zone 8
                    extract_mode = 'name',
                    is_loop=False
                )

                if is_break_loop_check:
                    break

                wait_for(
                    serial=serial,
                    detection_type='text',
                    target_file='con', 
                    sub_target_file='enter', 
                    text_action=lambda:[set_break_loop_check()], 
                    text_crop_area=(447, 391, 551, 429), # Nominating Contracts | zone 8
                    extract_mode = 'name',
                    is_loop=False
                )

                if is_break_loop_check:
                    break
            
            return is_last_event

        # วน loop ตาม match_slot_list
        for i in range(1, count_match + 1):
            ui_queue.put(('substage', serial, f'Event {i}'))
            current_slot = match_slot_list[i-1] if match_slot_list and i-1 < len(match_slot_list) else None
            prev_slot = match_slot_list[i-2] if match_slot_list and i > 1 and i-2 < len(match_slot_list) else 0

            # คำนวณว่าต้อง swipe กี่ครั้งเพื่อไปถึง slot นี้
            if current_slot:
                # ใช้ select mode: swipe จาก prev_slot ไป current_slot
                swipe_count = current_slot - prev_slot + 1 if prev_slot and current_slot > prev_slot else current_slot
                swipe_count = 1 if prev_slot and current_slot == prev_slot else swipe_count
            else:
                swipe_count = 0  # ไม่มี list ไม่ต้อง swipe

            print(f"Event {i}: current_slot={current_slot}, prev_slot={prev_slot}, swipe_count={swipe_count}")

            # Swipe ไปยัง event slot ที่ต้องการ
            for _ in range(swipe_count - 1):
                swipe_down(serial, swip_start[0], swip_start[1], swip_end[0], swip_end[1], duration_ms=5500)
                swipe_down(serial, swip_end[0], swip_end[1], swip_end[0], 300, duration_ms=1000)
                time.sleep(2)

            event_count = i
            is_enter = False
            def set_enter():
                nonlocal is_enter
                is_enter = True

            safe_ui_queue_put(('substage', serial, f'Event {event_count}'))
            is_last_event = loop_check()

            text_crop_area = (729, 391, 830, 429) if is_last_event else (447, 391, 551, 429)
            wait_for(
                serial=serial,
                detection_type='text',
                target_file='enter',
                text_action=lambda: [set_enter()],
                text_crop_area=text_crop_area,
                extract_mode='name',
                is_loop=False
            )

            safe_ui_queue_put(('substage', serial, f'Event {event_count}: กด Enter'))
            if is_last_event:
                tap_location(serial, 779, 413)
            else:
                tap_location(serial, 481, 413)

            if is_enter:
                loop_confirm_wait_for(
                    target_file='game',
                    text_action=lambda: [tap_location(serial, 481, 344)],
                    text_crop_area=(506, 173, 624, 205),
                )

            loop_farm_ai()

            # safe_ui_queue_put(('substage', serial, f'Event {event_count}: หน้า Check'))
            # wait_for(
            #     serial=serial,
            #     detection_type='text',
            #     target_file='check',
            #     text_action=lambda: [],
            #     text_crop_area=(452, 391, 527, 429),
            #     extract_mode='name'
            # )

            # ถ้าไม่ใช่ตัวสุดท้ายใน list ให้เตรียมสำหรับ slot ถัดไป
            if i < count_match:
                safe_ui_queue_put(('substage', serial, f'Event {event_count}: รอ Event ถัดไป'))
                # ไม่ต้อง swipe ที่นี่ เพราะจะคำนวณใน iteration ถัดไป
            else:
                # จบ loop ทั้งหมด
                loop_back_to_home(serial, wait_for, esc_key)
                break

    current_file, current_folder, num_name, accumulat = start_farm_mode(
        serial=serial,
        ui_queue=ui_queue
    )

    pre_stage()

    # Loop through stages from current_stage onwards
    for stage_no in range(current_stage, len(workflow) + 1):
        print(f"[FARM MODE] Starting stage {stage_no}/{len(workflow)}")
        logger.info(f"[FARM MODE] Starting stage {stage_no}/{len(workflow)} for device {serial}")
        
        # Execute farm stage logic
        try:
            
            if stage_no == 1:
                stage_1()
            
            handle_move_file(current_file, current_folder, [], num_name, mode='farm', accumulat=accumulat)
            
            # After completing the stage, update the stage in device_config
            if update_stage_func:
                update_stage_func(serial, stage_no)
                print(f"[FARM MODE] Saved progress: stage {stage_no}")
                logger.info(f"[FARM MODE] Saved progress: stage {stage_no} for device {serial}")
            
            time.sleep(1)  # Brief pause between stages
            
        except Exception as e:
            import traceback
            print(f"[FARM MODE] Error in stage {stage_no}: {str(e)}")
            logger.error(f"[FARM MODE] Error in stage {stage_no} for device {serial}: {str(e)}", exc_info=True)
            traceback.print_exc()
            # Save current progress before exiting
            if update_stage_func:
                update_stage_func(serial, stage_no)
            raise


    
    