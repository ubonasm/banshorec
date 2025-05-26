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
    page_title="板書記録・再現システム",
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
        if action['type'] == '消す（よける）':
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
            
        if action['type'] == '書く':
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
            if action['direction'] == '横書き':
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
        
        elif action['type'] == '線を引く':
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
        
        elif action['type'] == '囲う':
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
        
        elif action['type'] == '関連付ける':
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
    tab1, tab2, tab3 = st.tabs(["📝 板書記録", "▶️ 板書再現", "📊 データ管理"])
    
    with tab1:
        st.header("板書記録")
        
        # 授業記録CSVのアップロード
        uploaded_csv = st.file_uploader("授業記録CSVファイル（オプション）", type=['csv'])
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
            action_type = st.selectbox("アクションタイプ", ["書く", "消す（よける）", "線を引く", "囲う", "関連付ける"])
            
            if action_type == "書く":
                st.subheader("文字書き込み")
                content = st.text_input("書き込む文字")
                
                # 座標選択
                coord_options = get_grid_coordinates()
                start_coord = st.selectbox("書き始め座標", coord_options, key="text_start")
                end_coord = st.selectbox("書き終わり座標", coord_options, key="text_end")
                
                # 書字方向選択
                direction = st.radio("書字方向", ["横書き", "縦書き"])
                
                # スタイル設定
                color = st.color_picker("文字色", "#FFFFFF")
                size = st.slider("文字サイズ", 8, 24, 12)
                
                # 時間入力を追加
                default_time = len(st.session_state.actions)
                time_input = st.number_input("時間（秒）", min_value=0.0, value=float(default_time), step=0.1)
                
                if st.button("文字を記録"):
                    if content:
                        start_x, start_y = parse_coordinates(start_coord)
                        end_x, end_y = parse_coordinates(end_coord)
                        
                        action = {
                            'action_id': len(st.session_state.actions),  # ユニークID
                            'type': '書く',
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

            elif action_type == "消す（よける）":
                st.subheader("消去")
                
                # 消去可能なアクションを表示
                available_actions = []
                for i, action in enumerate(st.session_state.actions):
                    if action['type'] != '消す（よける）' and action.get('action_id', i) not in st.session_state.erased_actions:
                        if action['type'] == '書く':
                            available_actions.append((action.get('action_id', i), f"文字「{action['content']}」({action['start_x']},{action['start_y']})"))
                        elif action['type'] == '線を引く':
                            available_actions.append((action.get('action_id', i), f"線 ({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']})"))
                        elif action['type'] == '囲う':
                            available_actions.append((action.get('action_id', i), f"囲み ({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']})"))
                        elif action['type'] == '関連付ける':
                            available_actions.append((action.get('action_id', i), f"関連付け ({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']})"))
                
                if available_actions:
                    selected_action = st.selectbox("消去するオブジェクト", 
                                                 options=[aid for aid, desc in available_actions],
                                                 format_func=lambda x: next(desc for aid, desc in available_actions if aid == x))
                    
                    time_input = st.number_input("時間（秒）", min_value=0.0, value=float(len(st.session_state.actions)), step=0.1)
                    
                    if st.button("消去を記録"):
                        action = {
                            'action_id': len(st.session_state.actions),
                            'type': '消す（よける）',
                            'target_action_id': selected_action,
                            'time': time_input,
                            'timestamp': len(st.session_state.actions)
                        }
                        st.session_state.actions.append(action)
                        st.success("消去を記録しました")
                        st.rerun()
                else:
                    st.info("消去可能なオブジェクトがありません")

            elif action_type == "線を引く":
                st.subheader("線描画")
                coord_options = get_grid_coordinates()
                start_coord = st.selectbox("開始座標", coord_options, key="line_start")
                end_coord = st.selectbox("終了座標", coord_options, key="line_end")
                color = st.color_picker("線の色", "#FFFFFF")
                thickness = st.slider("線の太さ", 1, 10, 2)
                
                # 時間入力を追加
                default_time = len(st.session_state.actions)
                time_input = st.number_input("時間（秒）", min_value=0.0, value=float(default_time), step=0.1)
                
                if st.button("線を記録"):
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

            elif action_type == "囲う":
                st.subheader("囲み")
                coord_options = get_grid_coordinates()
                start_coord = st.selectbox("開始座標", coord_options, key="box_start")
                end_coord = st.selectbox("終了座標", coord_options, key="box_end")
                color = st.color_picker("囲みの色", "#FFFF00")
                
                # 時間入力を追加
                default_time = len(st.session_state.actions)
                time_input = st.number_input("時間（秒）", min_value=0.0, value=float(default_time), step=0.1)
                
                if st.button("囲みを記録"):
                    start_x, start_y = parse_coordinates(start_coord)
                    end_x, end_y = parse_coordinates(end_coord)
                    
                    action = {
                        'action_id': len(st.session_state.actions),
                        'type': '囲う',
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

            elif action_type == "関連付ける":
                st.subheader("関連付け")
                coord_options = get_grid_coordinates()
                start_coord = st.selectbox("開始座標", coord_options, key="rel_start")
                end_coord = st.selectbox("終了座標", coord_options, key="rel_end")
                color = st.color_picker("矢印の色", "#FFD93D")
                
                # 時間入力を追加
                default_time = len(st.session_state.actions)
                time_input = st.number_input("時間（秒）", min_value=0.0, value=float(default_time), step=0.1)
                
                if st.button("関連付けを記録"):
                    start_x, start_y = parse_coordinates(start_coord)
                    end_x, end_y = parse_coordinates(end_coord)
                    
                    action = {
                        'action_id': len(st.session_state.actions),
                        'type': '関連付ける',
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
                        if action['type'] == '書く':
                            st.write(f"{i+1}. 文字「{action['content']}」({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']}) [{action['direction']}] (Time: {action.get('time', action['timestamp'])})")
                        elif action['type'] == '消す（よける）':
                            st.write(f"{i+1}. 消去 (Action ID: {action['target_action_id']}) (Time: {action.get('time', action['timestamp'])})")
                        elif action['type'] == '線を引く':
                            st.write(f"{i+1}. 線 ({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']}) (Time: {action.get('time', action['timestamp'])})")
                        elif action['type'] == '囲う':
                            st.write(f"{i+1}. 囲み ({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']}) (Time: {action.get('time', action['timestamp'])})")
                        elif action['type'] == '関連付ける':
                            st.write(f"{i+1}. 関連付け ({action['start_x']},{action['start_y']})→({action['end_x']},{action['end_y']}) (Time: {action.get('time', action['timestamp'])})")
                    
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
        st.header("板書再現")
        
        if not st.session_state.actions:
            st.warning("記録されたアクションがありません。まず板書記録タブでアクションを記録してください。")
            return
        
        max_time = max([action.get('time', action['timestamp']) for action in st.session_state.actions])
        
        if max_time >= 0:
            # 再生制御
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("▶️ 再生"):
                    st.session_state.is_playing = True
            
            with col2:
                if st.button("⏸️ 一時停止"):
                    st.session_state.is_playing = False
            
            with col3:
                if st.button("⏹️ 停止"):
                    st.session_state.is_playing = False
                    st.session_state.current_time = 0
            
            with col4:
                st.session_state.playback_speed = st.selectbox("再生速度", [0.5, 1.0, 1.5, 2.0], index=1)
            
            with col5:
                if st.button("🔄 リセット"):
                    st.session_state.current_time = 0
                    st.session_state.is_playing = False
            
            # タイムスライダー
            playback_time = st.slider("再生時刻", 0.0, float(max_time), float(st.session_state.current_time), step=0.1)
            st.session_state.current_time = playback_time
            
            # 板書表示
            blackboard_html = create_blackboard_html(st.session_state.actions, st.session_state.current_time)
            st.components.v1.html(blackboard_html, height=GRID_HEIGHT * CELL_SIZE + 100)
            
            # タイムライン表示
            st.subheader("タイムライン")
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
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("データ保存")
            if st.session_state.actions:
                data_to_save = {
                    'actions': st.session_state.actions,
                    'metadata': {
                        'total_actions': len(st.session_state.actions),
                        'created_at': datetime.now().isoformat(),
                        'grid_size': f"{GRID_WIDTH}x{GRID_HEIGHT}"
                    }
                }
                
                json_str = json.dumps(data_to_save, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📥 板書データをダウンロード",
                    data=json_str,
                    file_name=f"blackboard_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            else:
                st.info("保存するデータがありません")
        
        with col2:
            st.subheader("データ読み込み")
            uploaded_file = st.file_uploader("板書データファイル", type=['json'])
            if uploaded_file is not None:
                try:
                    data = json.load(uploaded_file)
                    st.session_state.actions = data['actions']
                    st.success("データを読み込みました")
                    st.json(data.get('metadata', {}))
                    st.rerun()
                except Exception as e:
                    st.error(f"ファイル読み込みエラー: {e}")
        
        # 統計情報
        if st.session_state.actions:
            st.subheader("統計情報")
            
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
        
        # 記録管理機能
        st.subheader("記録管理")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**個別削除**")
            if st.session_state.actions:
                # 削除可能なアクションを選択
                delete_options = []
                for i, action in enumerate(st.session_state.actions):
                    if action['type'] == '書く':
                        delete_options.append((i, f"{i+1}. 文字「{action['content']}」"))
                    elif action['type'] == '消す（よける）':
                        delete_options.append((i, f"{i+1}. 消去 (ID: {action['target_action_id']})"))
                    elif action['type'] == '線を引く':
                        delete_options.append((i, f"{i+1}. 線"))
                    elif action['type'] == '囲う':
                        delete_options.append((i, f"{i+1}. 囲み"))
                    elif action['type'] == '関連付ける':
                        delete_options.append((i, f"{i+1}. 関連付け"))
                
                if delete_options:
                    selected_delete = st.selectbox(
                        "削除する記録を選択",
                        options=[idx for idx, desc in delete_options],
                        format_func=lambda x: next(desc for idx, desc in delete_options if idx == x)
                    )
                    
                    if st.button("選択した記録を削除", type="secondary"):
                        if st.checkbox("本当に削除しますか？", key="confirm_single_delete"):
                            deleted_action = st.session_state.actions.pop(selected_delete)
                            
                            # action_idを再割り当て
                            for j, act in enumerate(st.session_state.actions):
                                act['action_id'] = j
                            
                            # 削除されたアクションを参照している消去アクションも削除
                            st.session_state.actions = [
                                act for act in st.session_state.actions 
                                if not (act['type'] == '消す（よける）' and act.get('target_action_id') == deleted_action.get('action_id'))
                            ]
                            
                            st.success("記録を削除しました")
                            st.rerun()
                else:
                    st.info("削除可能な記録がありません")
            else:
                st.info("削除可能な記録がありません")

        with col2:
            st.write("**範囲削除**")
            if st.session_state.actions:
                start_idx = st.number_input("開始番号", min_value=1, max_value=len(st.session_state.actions), value=1)
                end_idx = st.number_input("終了番号", min_value=start_idx, max_value=len(st.session_state.actions), value=len(st.session_state.actions))
                
                if st.button("範囲削除", type="secondary"):
                    if st.checkbox("本当に削除しますか？", key="confirm_range_delete"):
                        # 指定範囲のアクションを削除（1-indexedから0-indexedに変換）
                        deleted_actions = st.session_state.actions[start_idx-1:end_idx]
                        st.session_state.actions = st.session_state.actions[:start_idx-1] + st.session_state.actions[end_idx:]
                        
                        # action_idを再割り当て
                        for j, act in enumerate(st.session_state.actions):
                            act['action_id'] = j
                        
                        # 削除されたアクションを参照している消去アクションも削除
                        deleted_action_ids = {act.get('action_id') for act in deleted_actions}
                        st.session_state.actions = [
                            act for act in st.session_state.actions 
                            if not (act['type'] == '消す（よける）' and act.get('target_action_id') in deleted_action_ids)
                        ]
                        
                        st.success(f"記録 {start_idx} から {end_idx} を削除しました")
                        st.rerun()
            else:
                st.info("削除可能な記録がありません")
        
        # データクリア
        if st.button("🗑️ 全データをクリア", type="secondary"):
            if st.checkbox("本当にクリアしますか？"):
                st.session_state.actions = []
                st.session_state.current_time = 0
                st.session_state.is_playing = False
                st.success("データをクリアしました")
                st.rerun()

if __name__ == "__main__":
    main()
