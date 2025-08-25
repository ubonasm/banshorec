import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import math

# ページ設定
st.set_page_config(
    page_title="Analyzing System for Board Writing",
    page_icon="📝",
    layout="wide"
)

# セッション状態の初期化
if 'actions' not in st.session_state:
    st.session_state.actions = []
if 'current_time' not in st.session_state:
    st.session_state.current_time = 0
if 'is_playing' not in st.session_state:
    st.session_state.is_playing = False
if 'playback_speed' not in st.session_state:
    st.session_state.playback_speed = 1.0
if 'lecture_records' not in st.session_state:
    st.session_state.lecture_records = None
# セッション状態に消去されたアクションIDを追跡
if 'erased_actions' not in st.session_state:
    st.session_state.erased_actions = set()
# 画像データを保存するための状態を追加
if 'uploaded_images' not in st.session_state:
    st.session_state.uploaded_images = {}

# 黒板のグリッド設定
GRID_WIDTH = 30
GRID_HEIGHT = 10
CELL_SIZE = 25  # 20から25に変更

def create_blackboard_html(actions, current_time=None):
    """黒板のHTMLを生成"""
    # 現在時刻までのアクションをフィルタリング
    if current_time is not None:
        filtered_actions = [action for action in actions if action.get('time', action['timestamp']) <= current_time]
    else:
        filtered_actions = actions
    
    # 消去されたアクションIDを追跡
    erased_action_ids = set()
    for action in filtered_actions:
        if action['type'] == 'erase':
            erased_action_ids.add(action['target_action_id'])
    
    html = f"""
    <div style="position: relative; margin: 10px auto;">
        <!-- 座標表示 -->
        <div style="position: absolute; left: 0; top: -20px; font-size: 12px; color: #666;">
            {"".join([f'<span style="position: absolute; left: {i * CELL_SIZE + 15}px;">{i}</span>' for i in range(0, GRID_WIDTH, 5)])}
        </div>
        <div style="position: absolute; left: -20px; top: 0; font-size: 12px; color: #666;">
            {"".join([f'<span style="position: absolute; top: {i * CELL_SIZE + 10}px;">{i}</span>' for i in range(0, GRID_HEIGHT, 2)])}
        </div>
        
        <!-- 黒板 -->
        <div style="
            width: {GRID_WIDTH * CELL_SIZE}px; 
            height: {GRID_HEIGHT * CELL_SIZE}px; 
            background-color: #2d5a2d; 
            position: relative; 
            border: 2px solid #fff;
            margin-left: 25px;
            margin-top: 25px;
        ">
    """
    
    # グリッド線を描画
    for i in range(GRID_WIDTH + 1):
        html += f"""
        <div style="
            position: absolute; 
            left: {i * CELL_SIZE}px; 
            top: 0; 
            width: 1px; 
            height: {GRID_HEIGHT * CELL_SIZE}px; 
            background-color: rgba(255,255,255,0.1);
        "></div>
        """
    
    for i in range(GRID_HEIGHT + 1):
        html += f"""
        <div style="
            position: absolute; 
            left: 0; 
            top: {i * CELL_SIZE}px; 
            width: {GRID_WIDTH * CELL_SIZE}px; 
            height: 1px; 
            background-color: rgba(255,255,255,0.1);
        "></div>
        """
    
    # アクションを描画（消去されていないもののみ）
    for action in filtered_actions:
        if action['type'] == '消す（よける）':
            continue
        if action.get('action_id') in erased_action_ids:
            continue
            
        if action['type'] == 'write words':
            # 文字の描画
            start_x = action['start_x'] * CELL_SIZE + CELL_SIZE // 2
            start_y = action['start_y'] * CELL_SIZE + CELL_SIZE // 2
            end_x = action['end_x'] * CELL_SIZE + CELL_SIZE // 2
            end_y = action['end_y'] * CELL_SIZE + CELL_SIZE // 2
            
            # 書き順の線を描画
            html += f"""
            <svg style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;">
                <line x1="{start_x}" y1="{start_y}" x2="{end_x}" y2="{end_y}" 
                      stroke="rgba(255,255,255,0.3)" stroke-width="1" stroke-dasharray="2,2"/>
            </svg>
            """
            
            # 文字の配置計算
            if action['direction'] == 'Horizontal writing (横書き)':
                text_x = start_x
                text_y = start_y
                writing_mode = 'horizontal-tb'
                text_orientation = 'mixed'
            else:
                text_x = start_x
                text_y = start_y
                writing_mode = 'vertical-rl'
                text_orientation = 'upright'
            
            html += f"""
            <div style="
                position: absolute; 
                left: {text_x - 10}px; 
                top: {text_y - 10}px; 
                color: {action['color']}; 
                font-size: {action['size']}px;
                font-weight: bold;
                writing-mode: {writing_mode};
                text-orientation: {text_orientation};
                white-space: nowrap;
                pointer-events: none;
            ">{action['content']}</div>
            """
            
            # 開始点と終了点のマーカー
            html += f"""
            <div style="
                position: absolute; 
                left: {start_x - 3}px; 
                top: {start_y - 3}px; 
                width: 6px; 
                height: 6px; 
                background-color: #00ff00; 
                border-radius: 50%;
                border: 1px solid white;
            " title="書き始め"></div>
            <div style="
                position: absolute; 
                left: {end_x - 3}px; 
                top: {end_y - 3}px; 
                width: 6px; 
                height: 6px; 
                background-color: #ff0000; 
                border-radius: 50%;
                border: 1px solid white;
            " title="書き終わり"></div>
            """
        
        elif action['type'] == 'draw the line':
            start_x = action['start_x'] * CELL_SIZE + CELL_SIZE // 2
            start_y = action['start_y'] * CELL_SIZE + CELL_SIZE // 2
            end_x = action['end_x'] * CELL_SIZE + CELL_SIZE // 2
            end_y = action['end_y'] * CELL_SIZE + CELL_SIZE // 2
            
            html += f"""
            <svg style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;">
                <line x1="{start_x}" y1="{start_y}" x2="{end_x}" y2="{end_y}" 
                      stroke="{action['color']}" stroke-width="{action['thickness']}"/>
            </svg>
            """
        
        elif action['type'] == 'surround':
            start_x = action['start_x'] * CELL_SIZE
            start_y = action['start_y'] * CELL_SIZE
            end_x = action['end_x'] * CELL_SIZE
            end_y = action['end_y'] * CELL_SIZE
            
            width = abs(end_x - start_x)
            height = abs(end_y - start_y)
            left = min(start_x, end_x)
            top = min(start_y, end_y)
            
            html += f"""
            <div style="
                position: absolute; 
                left: {left}px; 
                top: {top}px; 
                width: {width}px; 
                height: {height}px; 
                border: 2px solid {action['color']}; 
                border-radius: 5px;
                pointer-events: none;
            "></div>
            """
        
        elif action['type'] == 'relate':
            start_x = action['start_x'] * CELL_SIZE + CELL_SIZE // 2
            start_y = action['start_y'] * CELL_SIZE + CELL_SIZE // 2
            end_x = action['end_x'] * CELL_SIZE + CELL_SIZE // 2
            end_y = action['end_y'] * CELL_SIZE + CELL_SIZE // 2
            
            # 矢印の計算
            angle = math.atan2(end_y - start_y, end_x - start_x)
            arrow_length = 10
            arrow_angle = 0.5
            
            arrow_x1 = end_x - arrow_length * math.cos(angle - arrow_angle)
            arrow_y1 = end_y - arrow_length * math.sin(angle - arrow_angle)
            arrow_x2 = end_x - arrow_length * math.cos(angle + arrow_angle)
            arrow_y2 = end_y - arrow_length * math.sin(angle + arrow_angle)
            
            html += f"""
            <svg style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;">
                <line x1="{start_x}" y1="{start_y}" x2="{end_x}" y2="{end_y}" 
                      stroke="{action['color']}" stroke-width="2" stroke-dasharray="5,5"/>
                <polygon points="{end_x},{end_y} {arrow_x1},{arrow_y1} {arrow_x2},{arrow_y2}" 
                         fill="{action['color']}"/>
            </svg>
            """
        
        elif action['type'] == 'stick/ put':
            start_x = action['start_x'] * CELL_SIZE
            start_y = action['start_y'] * CELL_SIZE
            end_x = action['end_x'] * CELL_SIZE
            end_y = action['end_y'] * CELL_SIZE
            
            width = abs(end_x - start_x)
            height = abs(end_y - start_y)
            left = min(start_x, end_x)
            top = min(start_y, end_y)
            
            # 画像がある場合は画像を表示、ない場合は白い四角
            if action.get('image_id') and action['image_id'] in st.session_state.uploaded_images:
                image_info = st.session_state.uploaded_images[action['image_id']]
                image_data = image_info['data']
                image_type = image_info['type']
                
                html += f"""
                <div style="
                    position: absolute; 
                    left: {left}px; 
                    top: {top}px; 
                    width: {width}px; 
                    height: {height}px; 
                    border: 2px solid {action['border_color']}; 
                    border-radius: 3px;
                    overflow: hidden;
                    pointer-events: none;
                ">
                    <img src="data:{image_type};base64,{image_data}" 
                         style="width: 100%; height: 100%; object-fit: cover;" 
                         alt="{action['label']}" />
                </div>
                """
            else:
                # 代替表示（白い四角）
                html += f"""
                <div style="
                    position: absolute; 
                    left: {left}px; 
                    top: {top}px; 
                    width: {width}px; 
                    height: {height}px; 
                    background-color: {action['bg_color']}; 
                    border: 2px solid {action['border_color']}; 
                    border-radius: 3px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 10px;
                    color: #666;
                    pointer-events: none;
                ">{action['label']}</div>
                """
    
    html += "</div></div>"
    return html

def get_grid_coordinates():
    """グリッド座標の選択肢を生成"""
    coords = []
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            coords.append(f"({x},{y})")
    return coords

def parse_coordinates(coord_str):
    """座標文字列をパース"""
    coord_str = coord_str.strip("()");
    x, y = map(int, coord_str.split(","))
    return x, y

def main():
    st.title("📝 板書記録・再現システム")
    
    # タブの作成
    tab1, tab2, tab3 = st.tabs(["📝 Recording BW", "▶️ reproducing BW", "📊 Management data"])
    
    with tab1:
        st.header("Recording BW")
        
        # 授業記録CSVのアップロード
        uploaded_csv = st.file_uploader("transcript as CSV file (option)", type=['csv'])
        if uploaded_csv is not None:
            try:
                st.session_state.lecture_records = pd.read_csv(uploaded_csv)
                st.success("授業記録を読み込みました")
                st.dataframe(st.session_state.lecture_records.head())
            except Exception as e:
                st.error(f"CSVファイルの読み込みエラー: {e}")
        
        # アクション選択
        col1, col2 = st.columns([1, 2])
        
        with col1:
            action_type = st.selectbox("Teacher's Action", ["write", "erase", "draw the line", "surround", "relate", "stick/ put"])
            
            if action_type == "write":
                st.subheader("writing information")
                content = st.text_input("words")
                
                # 座標選択
                coord_options = get_grid_coordinates()
                start_coord = st.selectbox("Start coordinates", coord_options, key="text_start")
                end_coord = st.selectbox("End coordinates", coord_options, key="text_end")
                
                # 書字方向選択
                direction = st.radio("the way", ["Horizontal writing", "Vertical writing"])
                
                # スタイル設定
                color = st.color_picker("color", "#FFFFFF")
                size = st.slider("words size", 8, 24, 12)
                
                # 時間入力を追加
                default_time = len(st.session_state.actions)
                time_input = st.number_input("time（seconds）", min_value=0.0, value=float(default_time), step=0.1)
                
                if st.button("recording the words"):
                    if content:
                        start_x, start_y = parse_coordinates(start_coord)
                        end_x, end_y = parse_coordinates(end_coord)
                        
                        action = {
                            'action_id': len(st.session_state.actions),  # ユニークID
                            'type': 'write',
                            'content': content,
                            'start_x': start_x,
                            'start_y': start_y,
                            'end_x': end_x,
                            'end_y': end_y,
                            'direction': direction,
                            'color': color,
                            'size': size,
                            'time': time_input,  # 時間を追加
                            'timestamp': len(st.session_state.actions)
                        }
                        st.session_state.actions.append(action)
                        st.success(f"文字「{content}」を記録しました")
                        st.rerun()

            elif action_type == "erase":
                st.subheader("erase")
                
                # 消去可能なアクションを表示
                available_actions = []
                for i, action in enumerate(st.session_state.actions):
                    if action['type'] != 'erase' and action.get('action_id', i) not in st.session_state.erased_actions:
                        if action['type'] == 'write':
                            available_actions.append((action.get('action_id', i), f"文字「{action['content']}」({action['start_x']},{action['start_y']})"))
                        elif action['type'] == 'draw the line':
                            available_actions.append((action.get('action_id', i), f"線 ({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']})"))
                        elif action['type'] == 'surround':
                            available_actions.append((action.get('action_id', i), f"囲み ({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']})"))
                        elif action['type'] == 'relate':
                            available_actions.append((action.get('action_id', i), f"関連付け ({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']})"))
                        elif action['type'] == 'stick/ put':
                            available_actions.append((action.get('action_id', i), f"貼り付け「{action['label']}」({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']})"))
                
                if available_actions:
                    selected_action = st.selectbox("消去するオブジェクト", 
                                                 options=[aid for aid, desc in available_actions],
                                                 format_func=lambda x: next(desc for aid, desc in available_actions if aid == x))
                    
                    time_input = st.number_input("time（seconds）", min_value=0.0, value=float(len(st.session_state.actions)), step=0.1)
                    
                    if st.button("recording the erase"):
                        action = {
                            'action_id': len(st.session_state.actions),
                            'type': 'erase',
                            'target_action_id': selected_action,
                            'time': time_input,
                            'timestamp': len(st.session_state.actions)
                        }
                        st.session_state.actions.append(action)
                        st.success("消去を記録しました")
                        st.rerun()
                else:
                    st.info("消去可能なオブジェクトがありません")

            elif action_type == "draw the line":
                st.subheader("線描画")
                coord_options = get_grid_coordinates()
                start_coord = st.selectbox("Start coordinates", coord_options, key="line_start")
                end_coord = st.selectbox("End coordinates", coord_options, key="line_end")
                color = st.color_picker("color", "#FFFFFF")
                thickness = st.slider("width", 1, 10, 2)
                
                # 時間入力を追加
                default_time = len(st.session_state.actions)
                time_input = st.number_input("time（seconds）", min_value=0.0, value=float(default_time), step=0.1)
                
                if st.button("recording the line"):
                    start_x, start_y = parse_coordinates(start_coord)
                    end_x, end_y = parse_coordinates(end_coord)
                    
                    action = {
                        'action_id': len(st.session_state.actions),
                        'type': '線を引く',
                        'start_x': start_x,
                        'start_y': start_y,
                        'end_x': end_x,
                        'end_y': end_y,
                        'color': color,
                        'thickness': thickness,
                        'time': time_input,
                        'timestamp': len(st.session_state.actions)
                    }
                    st.session_state.actions.append(action)
                    st.success("線を記録しました")
                    st.rerun()

            elif action_type == "surround":
                st.subheader("囲み")
                coord_options = get_grid_coordinates()
                start_coord = st.selectbox("Start coordinates", coord_options, key="box_start")
                end_coord = st.selectbox("End coordinates", coord_options, key="box_end")
                color = st.color_picker("color", "#FFFF00")
                
                # 時間入力を追加
                default_time = len(st.session_state.actions)
                time_input = st.number_input("time（seconds）", min_value=0.0, value=float(default_time), step=0.1)
                
                if st.button("recording the surround"):
                    start_x, start_y = parse_coordinates(start_coord)
                    end_x, end_y = parse_coordinates(end_coord)
                    
                    action = {
                        'action_id': len(st.session_state.actions),
                        'type': 'surround',
                        'start_x': start_x,
                        'start_y': start_y,
                        'end_x': end_x,
                        'end_y': end_y,
                        'color': color,
                        'time': time_input,
                        'timestamp': len(st.session_state.actions)
                    }
                    st.session_state.actions.append(action)
                    st.success("囲みを記録しました")
                    st.rerun()

            elif action_type == "relate":
                st.subheader("関連付け")
                coord_options = get_grid_coordinates()
                start_coord = st.selectbox("Start coordinates", coord_options, key="rel_start")
                end_coord = st.selectbox("End coordinates", coord_options, key="rel_end")
                color = st.color_picker("color", "#FFD93D")
                
                # 時間入力を追加
                default_time = len(st.session_state.actions)
                time_input = st.number_input("time（seconds）", min_value=0.0, value=float(default_time), step=0.1)
                
                if st.button("recording the relationship"):
                    start_x, start_y = parse_coordinates(start_coord)
                    end_x, end_y = parse_coordinates(end_coord)
                    
                    action = {
                        'action_id': len(st.session_state.actions),
                        'type': 'relate',
                        'start_x': start_x,
                        'start_y': start_y,
                        'end_x': end_x,
                        'end_y': end_y,
                        'color': color,
                        'time': time_input,
                        'timestamp': len(st.session_state.actions)
                    }
                    st.session_state.actions.append(action)
                    st.success("関連付けを記録しました")
                    st.rerun()
            
            elif action_type == "stick/ put":
                st.subheader("貼り付け")
                coord_options = get_grid_coordinates()
                start_coord = st.selectbox("Start coordinates", coord_options, key="paste_start")
                end_coord = st.selectbox("End coordinates", coord_options, key="paste_end")
                
                # 画像アップロード機能
                uploaded_image = st.file_uploader("pictures of materials（option）", type=['png', 'jpg', 'jpeg', 'gif'], key="paste_image")
                
                # 代替表示の設定
                bg_color = st.color_picker("背景色", "#FFFFFF")
                border_color = st.color_picker("枠線色", "#000000")
                
                # ラベル（何を貼ったかの説明）
                label = st.text_input("labeling", placeholder="例：paper, picture, data etc.")
                
                # 時間入力を追加
                default_time = len(st.session_state.actions)
                time_input = st.number_input("time（seconds）", min_value=0.0, value=float(default_time), step=0.1)
                
                if st.button("recording the stick"):
                    start_x, start_y = parse_coordinates(start_coord)
                    end_x, end_y = parse_coordinates(end_coord)
                    
                    # 画像データの処理
                    image_id = None
                    if uploaded_image is not None:
                        image_id = f"image_{len(st.session_state.actions)}"
                        # 画像データをbase64エンコードして保存
                        import base64
                        image_data = base64.b64encode(uploaded_image.read()).decode()
                        st.session_state.uploaded_images[image_id] = {
                            'data': image_data,
                            'type': uploaded_image.type,
                            'name': uploaded_image.name
                        }
                    
                    action = {
                        'action_id': len(st.session_state.actions),
                        'type': 'stick/ put',
                        'start_x': start_x,
                        'start_y': start_y,
                        'end_x': end_x,
                        'end_y': end_y,
                        'bg_color': bg_color,
                        'border_color': border_color,
                        'label': label,
                        'image_id': image_id,
                        'time': time_input,
                        'timestamp': len(st.session_state.actions)
                    }
                    st.session_state.actions.append(action)
                    st.success(f"貼り付け「{label}」を記録しました")
                    st.rerun()
        
        with col2:
            st.subheader("現在の板書状態")
            if st.session_state.actions:
                blackboard_html = create_blackboard_html(st.session_state.actions)
                st.components.v1.html(blackboard_html, height=GRID_HEIGHT * CELL_SIZE + 100)
            else:
                empty_html = create_blackboard_html([])
                st.components.v1.html(empty_html, height=GRID_HEIGHT * CELL_SIZE + 100)
            
            # アクション履歴
            if st.session_state.actions:
                st.subheader("記録されたアクション")
                
                # 削除確認用のセッション状態
                if 'delete_confirm' not in st.session_state:
                    st.session_state.delete_confirm = {}
                
                for i, action in enumerate(st.session_state.actions):
                    col_text, col_delete = st.columns([4, 1])
                    
                    with col_text:
                        if action['type'] == 'write':
                            st.write(f"{i+1}. 文字「{action['content']}」({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']}) [{action['direction']}] (Time: {action.get('time', action['timestamp'])})")
                        elif action['type'] == 'erase':
                            st.write(f"{i+1}. 消去 (Action ID: {action['target_action_id']}) (Time: {action.get('time', action['timestamp'])})")
                        elif action['type'] == 'draw the line':
                            st.write(f"{i+1}. 線 ({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']}) (Time: {action.get('time', action['timestamp'])})")
                        elif action['type'] == 'surround':
                            st.write(f"{i+1}. 囲み ({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']}) (Time: {action.get('time', action['timestamp'])})")
                        elif action['type'] == 'relate':
                            st.write(f"{i+1}. 関連付け ({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']}) (Time: {action.get('time', action['timestamp'])})")
                        elif action['type'] == 'stick/ put':
                            st.write(f"{i+1}. 貼り付け「{action['label']}」({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']}) (Time: {action.get('time', action['timestamp'])})")
                    
                    with col_delete:
                        # 削除確認状態をチェック
                        confirm_key = f"confirm_delete_{i}"
                        if st.session_state.delete_confirm.get(confirm_key, False):
                            # 確認状態：本当に削除するかの最終確認
                            if st.button("本当に削除", key=f"really_delete_{i}", type="primary"):
                                # アクションを削除
                                deleted_action = st.session_state.actions.pop(i)
                                
                                # action_idを再割り当て
                                for j, act in enumerate(st.session_state.actions):
                                    act['action_id'] = j
                                
                                # 削除されたアクションを参照している消去アクションも削除
                                st.session_state.actions = [
                                    act for act in st.session_state.actions 
                                    if not (act['type'] == '消す（よける）' and act.get('target_action_id') == deleted_action.get('action_id'))
                                ]
                                
                                # 確認状態をリセット
                                st.session_state.delete_confirm[confirm_key] = False
                                st.success(f"アクション {i+1} を削除しました")
                                st.rerun()
                            
                            if st.button("キャンセル", key=f"cancel_delete_{i}"):
                                st.session_state.delete_confirm[confirm_key] = False
                                st.rerun()
                        else:
                            # 通常状態：削除ボタン
                            if st.button("🗑️", key=f"delete_{i}", help="この記録を削除"):
                                st.session_state.delete_confirm[confirm_key] = True
                                st.rerun()
    
    with tab2:
        st.header("Reproducting BW")
        
        if not st.session_state.actions:
            st.warning("記録されたアクションがありません。まず板書記録タブでアクションを記録してください。")
            return
        
        max_time = max([action.get('time', action['timestamp']) for action in st.session_state.actions])
        
        if max_time >= 0:
            # 再生制御
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("▶️ play"):
                    st.session_state.is_playing = True
            
            with col2:
                if st.button("⏸️ pause"):
                    st.session_state.is_playing = False
            
            with col3:
                if st.button("⏹️ stop"):
                    st.session_state.is_playing = False
                    st.session_state.current_time = 0
            
            with col4:
                st.session_state.playback_speed = st.selectbox("play speed", [0.5, 1.0, 1.5, 2.0], index=1)
            
            with col5:
                if st.button("🔄 reset"):
                    st.session_state.current_time = 0
                    st.session_state.is_playing = False
            
            # タイムスライダー
            playback_time = st.slider("再生時刻", 0.0, float(max_time), float(st.session_state.current_time), step=0.1)
            st.session_state.current_time = playback_time
            
            # 板書表示
            blackboard_html = create_blackboard_html(st.session_state.actions, st.session_state.current_time)
            st.components.v1.html(blackboard_html, height=GRID_HEIGHT * CELL_SIZE + 100)
            
            # タイムライン表示
            st.subheader("timeline")
            timeline_data = []
            for i, action in enumerate(st.session_state.actions):
                timeline_data.append({
                    'Time': action.get('time', action['timestamp']),
                    'Action': f"{action['type']} - {action.get('content', 'N/A')}",
                    'Type': action['type']
                })
            
            if timeline_data:
                df_timeline = pd.DataFrame(timeline_data)
                fig = px.scatter(df_timeline, x='Time', y='Action', color='Type', 
                               title="アクションタイムライン")
                fig.add_vline(x=st.session_state.current_time, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True)
            
            # 授業記録との同期表示
            if st.session_state.lecture_records is not None:
                st.subheader("授業記録（現在時刻周辺）")
                try:
                    # CSVファイルの列名を確認
                    if '時刻' in st.session_state.lecture_records.columns:
                        time_col = '時刻'
                    elif 'time' in st.session_state.lecture_records.columns:
                        time_col = 'time'
                    elif 'Time' in st.session_state.lecture_records.columns:
                        time_col = 'Time'
                    else:
                        time_col = st.session_state.lecture_records.columns[0]  # 最初の列を時刻として使用
                    
                    current_records = st.session_state.lecture_records[
                        (st.session_state.lecture_records[time_col] <= st.session_state.current_time + 5) &
                        (st.session_state.lecture_records[time_col] >= st.session_state.current_time - 5)
                    ]
                    if not current_records.empty:
                        st.dataframe(current_records)
                except Exception as e:
                    st.warning(f"授業記録の表示でエラーが発生しました: {e}")
                    st.dataframe(st.session_state.lecture_records.head())
            
            # 自動再生
            if st.session_state.is_playing and st.session_state.current_time < max_time:
                time.sleep(0.1)  # 0.1秒間隔で更新
                st.session_state.current_time += 0.1 * st.session_state.playback_speed
                st.rerun()
    
    with tab3:
        st.header("データ管理")
    
        # 起動時の読み込み機能を最上部に配置
        st.subheader("🚀 作業開始")
        st.write("保存した板書記録から作業を再開できます")
    
        # 読み込みモードの選択
        load_mode = st.radio(
            "読み込みモード",
            ["新規読み込み（現在のデータを置き換え）", "追加読み込み（現在のデータに追加）"],
            help="新規読み込み：保存したデータで完全に置き換え\n追加読み込み：現在の作業に保存したデータを追加"
        )
    
        uploaded_file = st.file_uploader("📁 板書データファイル（JSON）を選択", type=['json'], key="load_data_file")
    
        if uploaded_file is not None:
            try:
                # ファイル内容をプレビュー
                data = json.load(uploaded_file)
            
                st.write("**📋 ファイル内容プレビュー**")
                metadata = data.get('metadata', {})
            
                col_info1, col_info2, col_info3 = st.columns(3)
                with col_info1:
                    st.metric("アクション数", len(data.get('actions', [])))
                with col_info2:
                    st.metric("画像数", len(data.get('images', {})))
                with col_info3:
                    created_at = metadata.get('created_at', 'N/A')
                    if created_at != 'N/A':
                        try:
                            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            st.metric("作成日時", created_date.strftime('%Y/%m/%d %H:%M'))
                        except:
                            st.metric("作成日時", created_at)
                    else:
                        st.metric("作成日時", "N/A")
            
                # アクションの詳細プレビュー
                if data.get('actions'):
                    st.write("**📝 アクション一覧（最初の5件）**")
                    preview_actions = data['actions'][:5]
                    for i, action in enumerate(preview_actions):
                        if action['type'] == '書く':
                            st.write(f"{i+1}. 文字「{action['content']}」")
                        elif action['type'] == '貼る':
                            st.write(f"{i+1}. 貼り付け「{action.get('label', 'N/A')}」")
                        else:
                            st.write(f"{i+1}. {action['type']}")
                
                    if len(data['actions']) > 5:
                        st.write(f"...他 {len(data['actions']) - 5} 件")
            
                # 読み込み確認
                if load_mode.startswith("新規読み込み"):
                    if st.session_state.actions:
                        st.warning("⚠️ 現在の作業内容が削除されます。事前に保存することをお勧めします。")
                
                    if st.button("🔄 新規読み込み実行", type="primary"):
                        # 現在のデータをクリア
                        st.session_state.actions = []
                        st.session_state.uploaded_images = {}
                        st.session_state.current_time = 0
                        st.session_state.is_playing = False
                    
                        # 新しいデータを読み込み
                        st.session_state.actions = data['actions']
                    
                        # 画像データがある場合は復元
                        if 'images' in data:
                            st.session_state.uploaded_images = data['images']
                    
                        st.success(f"✅ データを読み込みました！（{len(data['actions'])}件のアクション）")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
            
                else:  # 追加読み込み
                    current_count = len(st.session_state.actions)
                    new_count = len(data['actions'])
                
                    if st.button("➕ 追加読み込み実行", type="primary"):
                        # action_idを調整して追加
                        for action in data['actions']:
                            action['action_id'] = len(st.session_state.actions)
                            action['timestamp'] = len(st.session_state.actions)
                            st.session_state.actions.append(action)
                    
                        # 画像データを追加
                        if 'images' in data:
                            for img_id, img_data in data['images'].items():
                                # 重複を避けるため新しいIDを生成
                                new_img_id = f"imported_{img_id}_{len(st.session_state.uploaded_images)}"
                                st.session_state.uploaded_images[new_img_id] = img_data
                            
                                # アクション内の画像IDも更新
                                for action in st.session_state.actions:
                                    if action.get('image_id') == img_id:
                                        action['image_id'] = new_img_id
                    
                        st.success(f"✅ データを追加しました！（{new_count}件のアクションを追加、合計{len(st.session_state.actions)}件）")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
        
            except json.JSONDecodeError:
                st.error("❌ JSONファイルの形式が正しくありません")
            except KeyError as e:
                st.error(f"❌ 必要なデータが見つかりません: {e}")
            except Exception as e:
                st.error(f"❌ ファイル読み込みエラー: {e}")
    
        else:
            st.info("📁 JSONファイルを選択してください")
        
            # 使用方法の説明
            with st.expander("💡 使用方法"):
                st.write("""
                **新規読み込み**
                - 保存したデータで現在の作業を完全に置き換えます
                - 途中で中断した作業を再開する場合に使用
            
                **追加読み込み**
                - 保存したデータを現在の作業に追加します
                - 複数のファイルを統合する場合に使用
            
                **注意事項**
                - 新規読み込みを行う前に、現在の作業を保存することをお勧めします
                - 画像データも含めて完全に復元されます
                """)
    
        st.divider()
    
        # データ保存・管理機能
        col1, col2 = st.columns(2)
    
        with col1:
            st.subheader("💾 save the data")
            if st.session_state.actions:
                data_to_save = {
                    'actions': st.session_state.actions,
                    'images': st.session_state.uploaded_images,  # 画像データも保存
                    'metadata': {
                        'total_actions': len(st.session_state.actions),
                        'created_at': datetime.now().isoformat(),
                        'grid_size': f"{GRID_WIDTH}x{GRID_HEIGHT}",
                        'version': '2.0'  # バージョン情報を追加
                    }
                }
            
                json_str = json.dumps(data_to_save, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📥 板書データをダウンロード",
                    data=json_str,
                    file_name=f"blackboard_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
                # 現在のデータ情報を表示
                st.write("**現在のデータ**")
                st.write(f"- アクション数: {len(st.session_state.actions)}件")
                st.write(f"- 画像数: {len(st.session_state.uploaded_images)}件")
            
            else:
                st.info("保存するデータがありません")
                st.write("板書記録タブでアクションを記録してから保存してください。")
    
        with col2:
            st.subheader("🗂️ 現在の作業状況")
            if st.session_state.actions:
                # 最新のアクション5件を表示
                st.write("**最新のアクション（5件）**")
                recent_actions = st.session_state.actions[-5:]
                for i, action in enumerate(reversed(recent_actions)):
                    idx = len(st.session_state.actions) - i
                    if action['type'] == '書く':
                        st.write(f"{idx}. 文字「{action['content']}」")
                    elif action['type'] == '貼る':
                        st.write(f"{idx}. 貼り付け「{action.get('label', 'N/A')}」")
                    else:
                        st.write(f"{idx}. {action['type']}")
            else:
                st.info("まだアクションが記録されていません")
                st.write("板書記録タブでアクションを記録してください。")
    
        # 統計情報
        if st.session_state.actions:
            st.subheader("📊 統計情報")
        
            # アクションタイプ別の集計
            action_counts = {}
            for action in st.session_state.actions:
                action_type = action['type']
                action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("総アクション数", len(st.session_state.actions))
            with col2:
                st.metric("記録時間", f"{len(st.session_state.actions)} ステップ")
            with col3:
                most_used = max(action_counts, key=action_counts.get) if action_counts else "なし"
                st.metric("最多使用アクション", most_used)
        
            # アクションタイプ分布
            if action_counts:
                fig = px.pie(values=list(action_counts.values()), 
                           names=list(action_counts.keys()), 
                           title="アクションタイプ分布")
                st.plotly_chart(fig, use_container_width=True)
    

if __name__ == "__main__":
    main()
