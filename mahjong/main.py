"""
마작 게임 메인 파일
분리된 모듈들을 통합하여 게임을 실행합니다.
"""

import pygame
import random
import json
import os
import math
from mahjong_resources import ResourceManager, SCREEN_WIDTH, SCREEN_HEIGHT, COLORS, TABLE_CENTER_X, TABLE_CENTER_Y, TILE_SIZE, TILE_SIZE_DISCARD, TILE_SIZE_WALL, get_resource_path
from mahjong_game import sort_hand, sort_hand_by_position, is_flower_tile, is_winning_hand
from mahjong_ai import ai_choose_discard
from discard_manager import DiscardManager
from wall_manager import WallManager
import time

def create_tiles():
    """마작 타일 생성 - 실제 파일 존재 여부 확인"""
    tiles = []
    
    # 수패: 만자, 통자 각각 1-9 * 4장
    suits = ['만', '통']
    for suit in suits:
        for num in range(1, 10):
            for copy in range(1, 5):
                tiles.append(f"{num}{suit}_{copy}.png")
    
    # 1삭은 꽃패로 사용하므로 포함 (2-9삭 이미지는 없음)
    for copy in range(1, 5):
        tiles.append(f"1삭_{copy}.png")
    
    # 풍패: 동남서북 각 4장
    winds = ['동', '남', '서', '북']
    for wind in winds:
        for copy in range(1, 5):
            tiles.append(f"{wind}_{copy}.png")
    
    # 삼원패: 중발백 각 4장
    dragons = ['중', '발', '백']
    for dragon in dragons:
        for copy in range(1, 5):
            tiles.append(f"{dragon}_{copy}.png")
    
    return tiles

class MahjongGame:
    # 논리 방향 <-> 화면 위치 매핑 상수
    DIRECTIONS = ['E', 'S', 'W', 'N']
    SCREENS = ['bottom', 'right', 'top', 'left']

    def __init__(self):
        pygame.init()
        pygame.mixer.init()  # 소리 시스템 초기화
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("한국 마작")
        self.clock = pygame.time.Clock()
        
        # 소리 로드
        try:
            click_sound_path = get_resource_path("click.wav")
            self.click_sound = pygame.mixer.Sound(click_sound_path)
        except:
            print("경고: click.wav 파일을 찾을 수 없습니다.")
            self.click_sound = None
        
        # 리소스 로드
        self.resources = ResourceManager()
        
        # 버림패 관리자 초기화
        self.discard_manager = DiscardManager(self.screen, self.resources)
        
        # 12게임 시스템 변수 초기화
        self.total_games = 12
        self.current_game = 1
        self.player_scores = [50, 50, 50, 50]  # 각 플레이어 시작 점수
        self.game_results = []  # 게임 결과 기록
        self.game_winner = None
        
        # 첫 게임 시작
        self.start_new_game()
    
    def play_click_sound(self):
        """클릭 소리 재생"""
        if self.click_sound:
            try:
                self.click_sound.play()
            except:
                pass  # 소리 재생 실패 시 무시
    
    def get_winning_hints(self, player_idx):
        """화료 가능한 패 힌트 반환 - 캐싱 적용"""
        if player_idx != self.player_index:
            return []  # 플레이어만 힌트 제공
        
        # 캐시 키 생성 (손패 + 멜드 + 꽃패)
        hand = self.hands[player_idx]
        melds = self.melds[player_idx]
        flower_count = len(self.flower_tiles[player_idx])
        
        # 캐시 키 생성
        cache_key = (tuple(sorted(hand)), len(melds), flower_count)
        
        # 캐시된 결과가 있으면 반환
        if hasattr(self, 'winning_hints_cache') and cache_key in self.winning_hints_cache:
            return self.winning_hints_cache[cache_key]
        
        # 실제 게임에서 사용 가능한 패들만 체크 (144장 대신 실제 가능한 패만)
        available_tiles = self.get_available_tiles_for_tenpai()
        
        winning_tiles = []
        
        # 각 패를 추가해서 화료 가능한지 체크
        for tile in available_tiles:
            # 이미 손패에 있는 패는 제외 (같은 패 5장은 불가능)
            if hand.count(tile) >= 4:
                continue
            
            # 1. 7쌍 패턴 체크 (멘젠 상태에서만)
            is_menzen = len(melds) == 0
            if is_menzen and len(hand) == 13:
                from mahjong_game import can_complete_seven_pairs_with_tile
                if can_complete_seven_pairs_with_tile(hand, tile):
                    winning_tiles.append(tile)
                    continue
            
            # 2. 기본 화료 패턴 체크
            temp_hand = hand + [tile]
            if self.check_winning_hand_with_melds_temp(player_idx, temp_hand, is_tsumo=True):
                winning_tiles.append(tile)
        
        # 중복 제거 및 정리
        result = self.organize_winning_hints(winning_tiles)
        
        # 캐시에 저장
        if not hasattr(self, 'winning_hints_cache'):
            self.winning_hints_cache = {}
        self.winning_hints_cache[cache_key] = result
        
        return result
    
    def organize_winning_hints(self, hints):
        """화료 힌트를 정리하여 중복 제거"""
        from mahjong_game import get_tile_base_name
        # 기본 이름별로 그룹화
        base_groups = {}
        for tile in hints:
            base_name = get_tile_base_name(tile)
            if base_name not in base_groups:
                base_groups[base_name] = []
            base_groups[base_name].append(tile)
        
        # 정리된 힌트 반환 (각 기본 이름당 하나씩)
        organized_hints = []
        for base_name, tiles in base_groups.items():
            organized_hints.append(tiles[0])  # 첫 번째 복사본 사용
        
        return organized_hints
    
    def can_riichi(self, player_idx):
        """엎어 가능 여부 체크 - 론이 가능한 상태에서만 엎어 가능"""
        if player_idx != self.player_index:
            return False  # 플레이어만 엎어 가능
        
        # 이미 엎어했으면 불가능
        if self.player_riichi:
            return False
        
        # 멜드가 있으면 엎어 불가능 (멘젠이 아니므로)
        if len(self.melds[player_idx]) > 0:
            return False
        
        # 론이 가능한 상태인지 체크 (다른 플레이어가 버린 패로 화료 가능)
        return self.can_ron_for_riichi(player_idx)
    
    def can_ron_for_riichi(self, player_idx):
        """엎어를 위한 론 가능 여부 체크 - 실제 게임에서 사용 가능한 패로 론이 가능한지"""
        hand = self.hands[player_idx]
        flower_count = len(self.flower_tiles[player_idx])
        
        # 실제 게임에서 사용 가능한 패들만 체크
        available_tiles = self.get_available_tiles_for_tenpai()
        
        for tile in available_tiles:
            # 임시로 패를 추가해서 론 가능한지 체크
            temp_hand = hand + [tile]
            
            # 멘젠 상태에서 론 가능한지 체크
            if self.check_winning_hand_with_melds_temp(player_idx, temp_hand, is_tsumo=False):
                return True
        
        return False
    
    def is_tenpai(self, player_idx):
        """간방 상태 체크 - 한 장만 들어오면 화료되는 상태"""
        hand = self.hands[player_idx]
        melds = self.melds[player_idx]
        flower_count = len(self.flower_tiles[player_idx])
        
        # 현재 손패로 화료 가능한지 먼저 체크
        if self.check_winning_hand_with_melds(player_idx, is_tsumo=True):
            return True
        
        # 간방 상태 체크: 실제 게임에서 사용 가능한 패들만 체크
        # (패산에 남아있는 패들 + 다른 플레이어가 버린 패들)
        available_tiles = self.get_available_tiles_for_tenpai()
        
        # 멘젠 여부 확인
        is_menzen = len(melds) == 0
        
        for tile in available_tiles:
            # 1. 7쌍 패턴 체크 (멘젠 상태에서만)
            if is_menzen and len(hand) == 13:
                from mahjong_game import can_complete_seven_pairs_with_tile
                if can_complete_seven_pairs_with_tile(hand, tile):
                    return True
            
            # 2. 기본 화료 패턴 체크
            temp_hand = hand + [tile]
            
            # 멜드를 포함한 화료 체크
            if self.check_winning_hand_with_melds_temp(player_idx, temp_hand, is_tsumo=True):
                return True
        
        return False
    
    def check_and_show_tenpai_dialog(self, player_idx):
        """간방 상태 체크 후 대기패 다이얼로그 표시 (대기패가 바뀌었을 때만)"""
        if player_idx != self.player_index:
            return  # 플레이어만 간방 다이얼로그 표시
        
        # 간방 상태 체크
        if self.is_tenpai(player_idx):
            # 화료 가능한 패 목록 가져오기
            waiting_tiles = self.get_winning_hints(player_idx)
            if waiting_tiles:
                # 대기패 목록을 정렬하여 비교
                sorted_waiting = sorted(waiting_tiles)
                sorted_last = sorted(getattr(self, 'last_tenpai_tiles', []))
                
                # 대기패가 바뀌었거나 처음 간방이 되었을 때만 다이얼로그 표시
                if sorted_waiting != sorted_last or not getattr(self, 'tenpai_dialog_shown', False):
                    print(f"🎯 간방 상태! 대기패: {len(waiting_tiles)}개")
                    self.show_tenpai_dialog(waiting_tiles)
                    self.last_tenpai_tiles = waiting_tiles.copy()
                    self.tenpai_dialog_shown = True
                    return True
                else:
                    # 대기패가 같으면 다이얼로그는 표시하지 않지만 상태는 유지
                    self.tenpai_waiting_tiles = waiting_tiles
                    self.player_tenpai_state = True
                    print(f"🎯 간방 상태 유지 (대기패 동일): {len(waiting_tiles)}개")
        else:
            # 간방 상태가 아니면 초기화 (하지만 기존 상태는 점진적으로 해제)
            if getattr(self, 'player_tenpai_state', False):
                print("🔄 간방 상태 해제")
            self.player_tenpai_state = False
            self.tenpai_waiting_tiles = []
            self.last_tenpai_tiles = []
            self.tenpai_dialog_shown = False
        
        return False
    
    def show_tenpai_dialog(self, waiting_tiles):
        """간방 상태 대기패 다이얼로그 표시"""
        self.tenpai_dialog_active = True
        self.tenpai_waiting_tiles = waiting_tiles
        self.player_tenpai_state = True
        
        print(f"🎯 === 간방 상태 ===")
        print(f"대기패: {len(waiting_tiles)}개")
        for i, tile in enumerate(waiting_tiles):
            from mahjong_game import get_tile_base_name
            tile_name = get_tile_base_name(tile)
            print(f"  {i+1}. {tile_name}")
        print(f"==================")
    
    def close_tenpai_dialog(self):
        """간방 다이얼로그 닫기"""
        self.tenpai_dialog_active = False
        self.tenpai_waiting_tiles = []
        self.tenpai_options = []
        print("🔄 간방 다이얼로그 닫음")
    
    def check_and_show_tenpai_dialog_with_drawn_tile(self, player_idx, drawn_tile):
        """뽑은 패를 포함한 간방 상태 체크 후 대기패 다이얼로그 표시"""
        if player_idx != self.player_index:
            return  # 플레이어만 간방 다이얼로그 표시
        
        # 뽑은 패를 임시로 손패에 추가한 상태로 간방 체크
        temp_hand = self.hands[player_idx] + [drawn_tile]
        melds = self.melds[player_idx]
        
        # 어떤 패를 버려야 간방이 되는지 분석
        tenpai_options = self.analyze_tenpai_options_with_drawn_tile(player_idx, drawn_tile)
        
        if tenpai_options:
            # 간방 옵션 정보를 정렬하여 비교 (옵션 변경 감지용)
            option_keys = []
            for option in tenpai_options:
                discard_tile = option['discard_tile']
                waiting_tiles = sorted(option['waiting_tiles'])
                option_keys.append((discard_tile, tuple(waiting_tiles)))
            
            sorted_current_options = sorted(option_keys)
            sorted_last_options = sorted(getattr(self, 'last_tenpai_options', []))
            
            # 간방 옵션이 바뀌었거나 처음 간방이 되었을 때만 다이얼로그 표시
            if sorted_current_options != sorted_last_options or not getattr(self, 'tenpai_dialog_shown', False):
                print(f"🎯 간방 옵션 발견! {len(tenpai_options)}가지 방법")
                self.show_tenpai_options_dialog(tenpai_options)
                self.last_tenpai_options = option_keys.copy()
                self.tenpai_dialog_shown = True
                
                # 첫 번째 옵션의 대기패를 상태로 저장 (지속 표시용)
                self.tenpai_waiting_tiles = tenpai_options[0]['waiting_tiles']
                self.player_tenpai_state = True
                return True
            else:
                # 옵션이 같으면 다이얼로그는 표시하지 않지만 상태는 유지
                self.tenpai_waiting_tiles = tenpai_options[0]['waiting_tiles']
                self.player_tenpai_state = True
                print(f"🎯 간방 옵션 유지 (동일): {len(tenpai_options)}가지")
        else:
            # 간방 상태가 아니면 초기화
            self.player_tenpai_state = False
            self.tenpai_waiting_tiles = []
            self.last_tenpai_options = []
            self.tenpai_dialog_shown = False
        
        return False
    
    def analyze_tenpai_options_with_drawn_tile(self, player_idx, drawn_tile):
        """뽑은 패를 포함해서 어떤 패를 버려야 간방이 되는지 분석"""
        if player_idx != self.player_index:
            return []
        
        temp_hand = self.hands[player_idx] + [drawn_tile]
        melds = self.melds[player_idx]
        is_menzen = len(melds) == 0
        
        # 실제 게임에서 사용 가능한 패들
        available_tiles = self.get_available_tiles_for_tenpai()
        
        tenpai_options = []
        
        # 각 패를 버리는 경우를 시뮬레이션
        for discard_candidate in temp_hand:
            # 해당 패를 버린 후의 손패 (13장)
            hand_after_discard = [t for t in temp_hand if t != discard_candidate]
            
            # 이 상태에서 화료 가능한 패들 찾기
            waiting_tiles = []
            
            for wait_tile in available_tiles:
                # 이미 손패에 4장 있으면 불가능
                if hand_after_discard.count(wait_tile) >= 4:
                    continue
                
                # 1. 7쌍 패턴 체크 (멘젠 상태에서만)
                if is_menzen and len(hand_after_discard) == 13:
                    from mahjong_game import can_complete_seven_pairs_with_tile
                    if can_complete_seven_pairs_with_tile(hand_after_discard, wait_tile):
                        waiting_tiles.append(wait_tile)
                        continue
                
                # 2. 기본 화료 패턴 체크
                test_hand = hand_after_discard + [wait_tile]
                if self.check_winning_hand_with_melds_temp(player_idx, test_hand, is_tsumo=True):
                    waiting_tiles.append(wait_tile)
            
            # 중복 제거
            unique_waiting_tiles = self.organize_winning_hints(waiting_tiles)
            
            if unique_waiting_tiles:
                from mahjong_game import get_tile_base_name
                discard_name = get_tile_base_name(discard_candidate)
                
                tenpai_options.append({
                    'discard_tile': discard_candidate,
                    'discard_name': discard_name,
                    'waiting_tiles': unique_waiting_tiles,
                    'waiting_count': len(unique_waiting_tiles)
                })
        
        # 중복 옵션 제거 (같은 버릴패 이름과 같은 대기패 조합)
        unique_options = []
        seen_combinations = set()
        
        for option in tenpai_options:
            # 버릴패 이름과 대기패 조합으로 중복 체크
            waiting_tiles_key = tuple(sorted(option['waiting_tiles']))
            combination_key = (option['discard_name'], waiting_tiles_key)
            
            if combination_key not in seen_combinations:
                seen_combinations.add(combination_key)
                unique_options.append(option)
        
        # 대기패 수가 많은 순으로 정렬
        unique_options.sort(key=lambda x: x['waiting_count'], reverse=True)
        
        return unique_options
    
    def show_tenpai_options_dialog(self, tenpai_options):
        """간방 옵션 다이얼로그 표시"""
        self.tenpai_dialog_active = True
        self.tenpai_options = tenpai_options
        self.player_tenpai_state = True
        
        print(f"🎯 === 간방 옵션 ===")
        for i, option in enumerate(tenpai_options):
            discard_name = option['discard_name']
            waiting_count = option['waiting_count']
            waiting_names = []
            for tile in option['waiting_tiles']:
                from mahjong_game import get_tile_base_name
                waiting_names.append(get_tile_base_name(tile))
            
            print(f"  {i+1}. {discard_name} 버리기 → 대기패 {waiting_count}개: {', '.join(waiting_names)}")
        print(f"====================")
    
    def get_available_tiles_for_tenpai(self):
        """간방 체크용 사용 가능한 패 목록 반환 - 버려진 패 제외"""
        # 버려진 패들을 수집
        discarded_tiles = []
        for discard_pile in self.discard_piles:
            discarded_tiles.extend(discard_pile)
        
        # 각 플레이어의 손패와 멜드에서 사용된 패들 수집
        used_tiles = []
        for i in range(4):
            used_tiles.extend(self.hands[i])
            for meld in self.melds[i]:
                if 'tiles' in meld:
                    used_tiles.extend(meld['tiles'])
        
        # 꽃패들도 제외
        for flower_tiles in self.flower_tiles:
            used_tiles.extend(flower_tiles)
        
        # 사용된 패들의 기본 이름 추출 (복사본 제거)
        from mahjong_game import get_tile_base_name
        used_base_tiles = set()
        for tile in used_tiles + discarded_tiles:
            base_name = get_tile_base_name(tile)
            used_base_tiles.add(base_name)
        
        # 사용 가능한 패들 생성 (사용되지 않은 패들만)
        available_tiles = []
        all_base_tiles = []
        
        # 숫자패 (1-9만, 1-9삭, 1-9통)
        for number in range(1, 10):
            for suit in ['만', '삭', '통']:
                base_name = f"{number}{suit}"
                all_base_tiles.append(base_name)
        
        # 바람패 (동, 남, 서, 북)
        for wind in ['동', '남', '서', '북']:
            all_base_tiles.append(wind)
        
        # 삼원패 (중, 발, 백)
        for dragon in ['중', '발', '백']:
            all_base_tiles.append(dragon)
        
        # 각 기본 패 타입에 대해 남은 개수 계산
        for base_name in all_base_tiles:
            # 해당 패가 몇 개 사용되었는지 계산
            used_count = sum(1 for used in used_base_tiles if used == base_name)
            
            # 4개 미만으로 사용되었다면 남은 개수만큼 추가
            remaining = 4 - used_count
            if remaining > 0:
                for i in range(remaining):
                    available_tiles.append(f"{base_name}_1.png")
        
        return available_tiles
    
    def get_all_possible_tiles(self):
        """모든 가능한 패 목록 반환"""
        tiles = []
        
        # 숫자패 (1-9만, 1-9삭, 1-9통)
        for number in range(1, 10):
            for suit in ['만', '삭', '통']:
                for copy in range(1, 5):  # 각 패 4장씩
                    tiles.append(f"{number}{suit}_{copy}.png")
        
        # 바람패 (동, 남, 서, 북)
        for wind in ['동', '남', '서', '북']:
            for copy in range(1, 5):
                tiles.append(f"{wind}_{copy}.png")
        
        # 삼원패 (중, 발, 백)
        for dragon in ['중', '발', '백']:
            for copy in range(1, 5):
                tiles.append(f"{dragon}_{copy}.png")
        
        return tiles
    
    def init_game_state(self):
        """게임 상태 초기화"""
        # 플레이어 설정
        self.player_index = 0  # 플레이어는 항상 인덱스 0
        self.players = ["플레이어", "AI동", "AI서", "AI북"]
        self.player_names = ["플레이어", "AI동", "AI서", "AI북"]
        self.player_positions = [0, 1, 2, 3]  # 플레이어 위치 (동남서북)
        
        # 게임 상태
        self.phase = 'dice'  # 'dice', 'deal_anim', 'playing', 'finished'
        self.game_phase = "dice_rolling"
        self.current_turn = 0
        self.turn_counter = 0
        self.waiting_for_player = False
        self.drawn_tile = None
        self.player_waiting = False  # 플레이어가 뜬 패 처리 대기 중
        self.last_player_turn_time = 0  # 플레이어 턴 시작 시간
        
        # 패 관련 - 완전히 새로 초기화
        from mahjong_game import init_player_game_data, init_game_flags
        
        self.wall_tiles = []
        
        # 플레이어별 게임 데이터 초기화
        player_data = init_player_game_data()
        self.hands = player_data['hands']
        self.discard_piles = player_data['discard_piles']
        self.flower_tiles = player_data['flower_tiles']
        self.melds = player_data['melds']
        
        # 패산 관리는 WallManager에 완전히 위임 - main.py에서는 추적하지 않음
        
        # WallManager 초기화 (기존 인스턴스가 있다면 제거)
        if hasattr(self, 'wall_manager'):
            del self.wall_manager
        self.wall_manager = None
        
        # 동가 관련
        self.east_player = None
        self.dice_results = []
        
        # 게임 플래그들 초기화
        game_flags = init_game_flags()
        for key, value in game_flags.items():
            setattr(self, key, value)
        
        # 엎어 관련
        self.player_riichi = False  # 플레이어가 엎어했는지
        self.riichi_bonus = 1  # 엎어 보너스 점수
        
        # 예약된 페이즈 전환
        self.scheduled_phase = None
        self.scheduled_time = None
        
        # 화면 위치 매핑 업데이트
        self.update_screen_positions()
        
        # 무한 루프 방지용 카운터들
        self.max_turns = 200
        self.max_wall_draws = 100
    
    def update_screen_positions(self):
        """플레이어 위치에 따른 화면 매핑 업데이트"""
        # 기본 매핑 (동가가 결정되기 전)
        if self.east_player is None:
            self.screen_to_player = {
                'bottom': 0,  # 플레이어
                'right': 1,   # AI동
                'top': 2,     # AI서  
                'left': 3     # AI북
            }
        else:
            # 동가가 결정된 후 매핑
            positions = [(self.east_player + i) % 4 for i in range(4)]
            self.screen_to_player = {
                'bottom': positions[0],  # 동가
                'right': positions[1],   # 남가
                'top': positions[2],     # 서가
                'left': positions[3]     # 북가
            }
    
    def get_player_screen_position(self, player_idx):
        """플레이어의 화면 위치 반환"""
        for screen_pos, pos in self.screen_to_player.items():
            if pos == player_idx:
                return screen_pos
        return None

    def start_new_game(self):
        """새로운 게임 시작"""
        print(f"=== 새로운 마작 게임 시작 ({self.current_game}/{self.total_games}판) ===")
        
        # 게임 상태 초기화
        self.init_game_state()
        
        # 플레이어 이름 설정
        self.player_names = ["플레이어", "김민수", "박지영", "이준호"]
        self.players = ["human", "ai", "ai", "ai"]
        
        # 화면 위치 매핑 (플레이어는 항상 하단)
        self.screen_to_player = {
            'bottom': 0,  # 플레이어
            'right': 1,   # AI1
            'top': 2,     # AI2
            'left': 3     # AI3
        }
        
        # 첫 게임만 주사위로 동가 결정, 이후는 화료자가 동가
        if self.current_game == 1:
            # 1단계: 주사위 던지기로 동가 결정
            self.start_dice_rolling()
        else:
            # 이전 게임 결과에 따라 동가 결정 (한국 마작 규칙)
            if hasattr(self, 'game_winner') and self.game_winner is not None:
                # 화료한 플레이어가 동가
                self.east_player = self.game_winner
                print(f"🏆 이전 게임 화료자 {self.player_names[self.game_winner]}이 동가가 됩니다.")
            else:
                # 무승부(유국)면 이전 동가 유지
                if hasattr(self, 'east_player') and self.east_player is not None:
                    print(f"🤝 유국으로 이전 동가 {self.player_names[self.east_player]} 유지")
                else:
                    # 예외 상황: 동가가 설정되지 않은 경우 기본값 설정
                    self.east_player = 0
                    print(f"🎲 동가: {self.player_names[self.east_player]} (기본값)")
        
        # 2단계: 동가 결정 후 플레이어 이름 업데이트
        self.update_player_names_with_positions()
        
        # 3단계: 패산 구성 (동가 결정 후)
        self.wall_tiles = create_tiles()
        print(f"[DEBUG] create_tiles() -> {len(self.wall_tiles)}장")
        random.shuffle(self.wall_tiles)
        print(f"[DEBUG] self.wall_tiles after shuffle -> {len(self.wall_tiles)}장")
        
        # 패산 관리자 초기화 (패산 생성 후)
        self.wall_manager = WallManager(self.wall_tiles, self.screen)
        
        # 4단계: 주사위 단계 또는 배패 시작
        if self.current_game == 1:
            # 첫 게임: 동가 결정 주사위 + 패산 주사위
            self.phase = 'dice'
            # 주사위는 이미 start_dice_rolling()에서 던져짐
        else:
            # 2판부터는 동가는 이미 결정됨 → 패산 주사위만 던지고 시작
            print(f"🎲 동가: {self.player_names[self.east_player]}")
            self.phase = 'dice'
            self.dice_step = 'wall_only'
            self.roll_dice_for_wall_position()
            self.waiting_for_user_input = True
        
        print("=== 게임 시작 ===")
        
    def update_player_names_with_positions(self):
        """동가 결정 후 플레이어 이름에 위치 정보 추가"""
        positions = ['동가', '남가', '서가', '북가']
        base_names = ["플레이어", "김민수", "박지영", "이준호"]
        
        for i in range(4):
            # 동가로부터의 상대적 위치 계산
            relative_pos = (i - self.east_player) % 4
            position_name = positions[relative_pos]
            
            # 기본 이름에 위치 정보 추가
            self.player_names[i] = f"{base_names[i]}({position_name})"
        
        # 화면 위치 정보 출력
        for screen_pos, player_idx in self.screen_to_player.items():
            marker = " ← 나" if player_idx == 0 else ""
            print(f"{screen_pos}: {self.player_names[player_idx]}{marker}")
        print()

    def start_dice_rolling(self):
        """주사위 던지기로 동가 결정 (첫 게임에만 사용)"""
        print("\n=== [첫 게임] 주사위 던지기로 동가 결정 ===")
        
        # 주사위 결과 생성
        self.dice_results = []
        for i in range(4):
            dice1 = random.randint(1, 6)
            dice2 = random.randint(1, 6)
            total = dice1 + dice2
            self.dice_results.append((dice1, dice2, total))
            print(f"플레이어 {i}: {dice1} + {dice2} = {total}")
        
        # 가장 높은 점수를 받은 플레이어가 동가
        max_total = max(result[2] for result in self.dice_results)
        self.east_player = next(i for i, result in enumerate(self.dice_results) if result[2] == max_total)
        
        print(f"🎲 주사위 결과: 플레이어 {self.east_player}이 동가로 결정됨 (점수: {max_total})")
        print(f"🎯 첫 게임 동가: {self.east_player}번 플레이어")
        print(f"📝 이후 게임: 화료자가 동가, 유국시 동가 유지")
        
        # 첫 게임에서는 동가 결정 후 패산 주사위 단계로
        if self.current_game == 1:
            self.dice_step = 'east'  # 동가 결정 완료
            self.waiting_for_user_input = True
        else:
            # 이후 게임에서는 패산 주사위만
            self.dice_step = 'wall_only'
            self.roll_dice_for_wall_position()
            self.waiting_for_user_input = True
    
    def roll_dice_for_wall_position(self):
        """패산 시작 위치 결정을 위한 주사위 던지기"""
        print(f"\n=== 패산 시작 위치 결정을 위한 주사위 던지기 ===")
        
        # 주사위 2개 던지기
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        dice_total = dice1 + dice2
        
        # 주사위 결과 저장 (화면 표시용)
        self.wall_dice_results = (dice1, dice2, dice_total)
        
        print(f"🎲 주사위 결과: {dice1} + {dice2} = {dice_total}")
        
        # 패산 시작 위치 설정
        self.set_wall_start_position(dice_total)
    
    def set_wall_start_position(self, dice_total):
        """주사위 결과로 패산 시작 위치 설정"""
        # 동가 위치부터 시계방향으로 주사위 수만큼 이동
        wall_position_idx = (self.east_player + dice_total - 1) % 4
        self.wall_start_position = wall_position_idx
        
        # 화면 위치로 변환 (플레이어 인덱스 → 화면 위치)
        screen_positions = ['bottom', 'right', 'top', 'left']  # 0=플레이어, 1=오른쪽AI, 2=위AI, 3=왼쪽AI
        wall_screen_pos = screen_positions[wall_position_idx]
        
        # 한국 마작 규칙: 주사위 합에서 해당 플레이어 앞 패산의 오른쪽부터 세어서 시작
        # 주사위 합이 시작 스택 번호가 됨 (1-based를 0-based로 변환)
        start_stack = (dice_total - 1) % 13
        start_layer = 1  # 위층부터 시작
        
        # 플레이어 방향 정보 생성 (동가 기준으로 시계방향)
        directions = ['동', '남', '서', '북']  # 시계방향 순서
        screen_positions = ['bottom', 'right', 'top', 'left']  # 시계방향 화면 순서
        player_directions = {}
        
        for i, screen_pos in enumerate(screen_positions):
            # 각 화면 위치에 해당하는 플레이어 인덱스 찾기
            player_idx = i  # 0=bottom(플레이어), 1=right, 2=top, 3=left
            # 동가로부터의 상대적 위치 계산
            relative_pos = (player_idx - self.east_player) % 4
            direction = directions[relative_pos]
            player_directions[screen_pos] = direction
        
        # WallManager에 주사위 결과와 방향 정보 전달
        if hasattr(self, 'wall_manager'):
            self.wall_manager.set_dice_start_position(dice_total, player_directions)
        
        print(f"🎲 패산 시작 위치 설정 완료 (주사위 합: {dice_total})")
    
    def handle_dice_input(self):
        """주사위 단계에서 사용자 입력 처리"""
        if not hasattr(self, 'waiting_for_user_input') or not self.waiting_for_user_input:
            return
            
        self.waiting_for_user_input = False
        
        if self.dice_step == 'east':
            # 동가 결정 후 패산 주사위로 진행
            self.dice_step = 'wall'
            self.roll_dice_for_wall_position()
            self.waiting_for_user_input = True
        elif self.dice_step == 'wall' or self.dice_step == 'wall_only':
            # 패산 주사위 후 배패 시작
            self.dice_step = 'complete'
            self.phase = 'deal_anim'  # phase도 변경
            self.start_deal_animation()
    
    def schedule_next_phase(self, delay_ms):
        """다음 단계 예약 - 간소화"""
        self.next_turn_time = pygame.time.get_ticks() + delay_ms
    
    def check_scheduled_phase(self):
        """예약된 단계 확인"""
        if hasattr(self, 'next_turn_time') and self.next_turn_time > 0 and pygame.time.get_ticks() >= self.next_turn_time:
            self.next_turn_time = 0
            
            if self.phase == 'dice':
                # 주사위 → 배패 애니메이션 시작
                print(f"⏰ === 배패 애니메이션 자동 시작 ===")
                self.phase = 'deal_anim'
                self.game_phase = 'deal_anim'
                self.start_deal_animation()
    
    def start_deal_animation(self):
        """배패 애니메이션 시작"""
        # 배패 순서 생성 (동가부터 시계방향)
        self.temp_deal_order = self.get_deal_order()
        print(f"[DEBUG] 배패 순서 생성: {len(self.temp_deal_order)}장")
        
        # WallManager 상태 확인 (배패 시작 전)
        print(f"[DEBUG] 배패 시작 전 WallManager 상태:")
        debug_info = self.wall_manager.get_debug_info()
        print(f"  - dealt_tiles: {debug_info['dealt_tiles']}장")
        print(f"  - remaining_tiles: {debug_info['remaining_tiles']}장")
        print(f"  - current_position: {debug_info['current_position']}")
        print(f"  - wang_position: {debug_info['wang_position']}")
        
        # 배패 애니메이션 상태 초기화
        self.phase = 'deal_anim'
        self.deal_anim_index = 0
        self.deal_anim_last_time = pygame.time.get_ticks()
        self.temp_hands = [[] for _ in range(4)]
        self.temp_flower_tiles = [[] for _ in range(4)]
        
        print("🎮 배패 애니메이션 시작!")
    
    def get_deal_order(self):
        """배패 순서 생성 - 동가부터 시계방향"""
        # 동-남-서-북 순서 인덱스
        deal_order_indices = [(self.east_player + i) % 4 for i in range(4)]
        order = []
        
        # 3라운드: 각자 4장씩 (총 12장)
        for _ in range(3):
            for idx in deal_order_indices:
                for _ in range(4):
                    order.append(idx)
        
        # 마지막 라운드: 각자 1장씩 (총 13장), 동가는 1장 더 (총 14장)
        for idx in deal_order_indices:
            order.append(idx)
        
        # 동가에게 마지막 1장 추가 (14장 완성)
        order.append(self.east_player)
        
        return order
    
    def deal_tiles(self):
        """배패 - 각자 13장씩, 동가는 14장 (시계방향 패산 뽑기)"""
        print("=== 배패 시작 ===")
        
        # 초기화
        self.hands = [[] for _ in range(4)]
        self.flower_tiles = [[] for _ in range(4)]
        # 패산 관리는 WallManager에 완전히 위임
        
        # 각자 13장씩 배패
        for round_num in range(3):  # 3라운드
            print(f"\n--- 배패 라운드 {round_num + 1} ---")
            for player_idx in range(4):
                for _ in range(4):  # 4장씩
                    tile = self.draw_tile_from_wall()
                    if tile:
                        self.assign_tile_to_player(player_idx, tile)
        
        # 마지막 배패: 각자 1장씩, 동가는 2장
        print(f"\n--- 마지막 배패 ---")
        for player_idx in range(4):
            if player_idx == self.east_player:  # 동가
                for _ in range(2):
                    tile = self.draw_tile_from_wall()
                    if tile:
                        self.assign_tile_to_player(player_idx, tile)
            else:
                tile = self.draw_tile_from_wall()
                if tile:
                    self.assign_tile_to_player(player_idx, tile)
        
        # 손패 정렬 - 각 플레이어 위치에 따라
        for i in range(4):
            player_position = self.get_player_screen_position(i)
            self.hands[i] = sort_hand_by_position(self.hands[i], player_position)
        
        print("\n=== 배패 완료! ===")
        for i, (name, hand) in enumerate(zip(self.player_names, self.hands)):
            flower_count = len(self.flower_tiles[i])
            print(f"{name}: {len(hand)}장 + 꽃패 {flower_count}장 {self.flower_tiles[i]}")
            
        # 전체 패 개수 확인 - WallManager 사용
        total_hand_tiles = sum(len(hand) for hand in self.hands)
        total_flower_tiles = sum(len(flowers) for flowers in self.flower_tiles)
        remaining_tiles = self.wall_manager.get_remaining_tiles_count()
        print(f"📊 총 패 분포: 손패 {total_hand_tiles}장 + 꽃패 {total_flower_tiles}장 + 패산 {remaining_tiles}장 = {total_hand_tiles + total_flower_tiles + remaining_tiles}장")
    
    def assign_tile_to_player(self, player_idx, tile):
        """플레이어에게 패 할당 (꽃패 처리 포함) - 무한 루프 방지"""
        max_attempts = 3  # 최대 시도 횟수 더 줄임 (5 → 3)
        attempts = 0
        player_name = self.player_names[player_idx]
        
        # 배패 중에는 디버그 메시지 줄이기
        if self.game_phase != "dice_rolling":
            print(f"🎴 {player_name}에게 패 할당: {tile}")
        
        # 무한 루프 방지를 위한 추가 체크
        original_tile = tile
        
        while is_flower_tile(tile) and attempts < max_attempts:
            if self.game_phase != "dice_rolling":
                print(f"🌸 {player_name}이 꽃패 받음: {tile} (시도: {attempts + 1}/{max_attempts})")
            self.flower_tiles[player_idx].append(tile)
            attempts += 1
            
            # 꽃패 대체용 패 뽑기
            replacement_tile = self.draw_tile_from_wall()
            if replacement_tile:
                tile = replacement_tile
                if self.game_phase != "dice_rolling":
                    print(f"🎴 대체 패 뽑음: {tile}")
                
                # 같은 패가 반복되면 강제 중단
                if tile == original_tile:
                    if self.game_phase != "dice_rolling":
                        print(f"⚠️ 같은 패 반복됨, 강제 중단: {tile}")
                    break
            else:
                if self.game_phase != "dice_rolling":
                    print("⚠️ 패산이 비어서 꽃패 대체 중단")
                break
        
        # 최종적으로 받은 패가 꽃패가 아니면 손패에 추가
        if not is_flower_tile(tile):
            self.hands[player_idx].append(tile)
            if self.game_phase != "dice_rolling":
                print(f"✅ {player_name} 손패에 추가: {tile}")
        else:
            # 최대 시도 횟수를 초과했지만 여전히 꽃패라면 강제로 손패에 추가
            if self.game_phase != "dice_rolling":
                print(f"⚠️ 꽃패 처리 중 최대 시도 횟수 초과 또는 반복: {tile}")
            self.hands[player_idx].append(tile)
    
    def draw_tile_from_wall(self):
        """패산에서 패 한 장 뽑기 - WallManager 사용"""
        result = self.wall_manager.draw_regular_tile()
        if result is None:
            return None
            
        tile, tile_index = result
        print(f"[DEBUG] 패산에서 패 뽑음: 인덱스={tile_index}, 패={tile}, 남은패={self.wall_manager.get_remaining_tiles_count()}장")
        return tile
    
    def draw_flower_replacement_tile(self):
        """왕패(패산 뒤쪽)에서 꽃패 보충용 패 뽑기 - WallManager 사용"""
        result = self.wall_manager.draw_wang_tile()
        if result is None:
            return None
            
        tile, tile_index = result
        print(f"[DEBUG] 왕패에서 보충패 뽑음: 인덱스={tile_index}, 패={tile}")
        return tile
    
    def get_flower_replacement_tile_index_runtime(self):
        """게임 진행 중 꽃패 보충용 왕패 인덱스 계산 - WallManager 사용"""
        # WallManager에서 다음 왕패 인덱스 가져오기
        return self.wall_manager.get_next_wang_tile_index()
    
    def get_next_wall_tile_index(self):
        """시계방향으로 다음에 뽑을 패의 인덱스 계산 - WallManager 사용"""
        # WallManager에서 다음 일반 패 인덱스 가져오기
        return self.wall_manager.get_next_regular_tile_index()

    def advance_turn(self):
        """다음 턴으로 진행 - 단순화된 로직"""
        print(f"\n🔄 === advance_turn() 시작 (턴 #{self.turn_counter}) ===")
        
        # 무한 루프 방지
        self.turn_counter += 1
        if self.turn_counter > self.max_turns:
            print(f"🚫 최대 턴 수({self.max_turns}) 초과! 게임 강제 종료")
            self.game_winner = None
            self.finish_game("draw", None)
            return
        
        # 패산이 비었으면 유국 - WallManager 사용
        if self.wall_manager.get_remaining_tiles_count() <= 0:
            print(f"\n🚫 패산이 비어서 유국!")
            self.game_winner = None
            self.finish_game("draw", None)
            return
            
        # 다음 플레이어로 턴 변경
        old_turn = self.current_turn
        self.current_turn = (self.current_turn + 1) % 4
        current_name = self.player_names[self.current_turn]
        
        print(f"🔄 턴 변경: {old_turn} → {self.current_turn}")
        print(f"새로운 턴: {current_name}")
        
        # 턴 시작
        self.start_turn()
        
        print(f"🔄 === advance_turn() 완료 ===\n")

    def start_turn(self):
        """현재 플레이어의 턴 시작"""
        current_name = self.player_names[self.current_turn]
        print(f"\n⭐ === {current_name} 턴 시작 ===")
        
        if self.current_turn == self.player_index:
            # 플레이어 턴
            self.start_player_turn()
        else:
            # AI 턴
            self.start_ai_turn()

    def start_player_turn(self):
        """플레이어 턴 시작"""
        print("👤 플레이어 턴 시작")
        
        # 클릭 버퍼 초기화 (새 턴 시작 시)
        self.clear_click_buffer()
        self.last_player_turn_time = pygame.time.get_ticks()
        
        # 현재 손패 수와 멜드 수 확인
        current_hand_size = len(self.hands[self.player_index])
        meld_count = len(self.melds[self.player_index])
        
        print(f"🎯 플레이어 상태: 손패={current_hand_size}장, 멜드={meld_count}개")
        
        # 멜드를 고려한 예상 손패 수 계산 (한국 마작 규칙)
        # 기본: 13장 + 뽑은패 1장 = 14장 → 1장 버리기 → 13장
        # 멜드 1개: 13 - 3 = 10장 + 뽑은패 1장 = 11장 → 1장 버리기 → 10장  
        # 멜드 2개: 13 - 6 = 7장 + 뽑은패 1장 = 8장 → 1장 버리기 → 7장
        expected_hand_size_for_discard = 14 - (meld_count * 3)  # 패를 버려야 하는 상태
        expected_hand_size_for_draw = 13 - (meld_count * 3)     # 패를 뽑아야 하는 상태
        
        print(f"🔧 예상 패 수: 뽑기={expected_hand_size_for_draw}장, 버리기={expected_hand_size_for_discard}장")
        
        # 첫 턴 체크 (배패 직후 14장) 또는 펑/깡 후 패 버리기 상태
        if current_hand_size == expected_hand_size_for_discard:
            if meld_count == 0:
                print("🎯 첫 턴: 14장에서 1장 버리기")
            else:
                print(f"🎯 펑/깡 후: {current_hand_size}장에서 1장 버리기")
            self.drawn_tile = None
            self.waiting_for_player = True
            return
        
        # 손패 수가 예상과 다른 경우 경고
        if current_hand_size != expected_hand_size_for_draw:
            print(f"⚠️ 손패 수 불일치: {current_hand_size}장 (예상: {expected_hand_size_for_draw}장, 멜드: {meld_count}개)")
            # 그래도 계속 진행
        
        # 일반 턴: 패 뽑기
        drawn = self.draw_tile_from_wall()
        if drawn is None:
            print("🚫 패산이 비어서 유국!")
            self.game_winner = None
            self.finish_game("draw", None)
            return
            
        # 꽃패 처리 - 왕패에서 보충
        while is_flower_tile(drawn):
            print(f"🌸 꽃패 받음: {drawn}")
            self.flower_tiles[self.player_index].append(drawn)
            drawn = self.draw_flower_replacement_tile()
            if drawn is None:
                print("🚫 왕패가 비어서 유국!")
                self.game_winner = None
                self.finish_game("draw", None)
                return
        
        # 뜬 패를 손패에 바로 추가하지 않고 따로 보관
        self.drawn_tile = drawn
        self.player_waiting = True  # 플레이어가 뜬 패 처리 대기 중
        print(f"✅ 패 뽑음: {drawn}")
        
        # 뽑은 패로 화료 체크 (임시로 손패에 추가해서 체크)
        temp_hand = self.hands[self.player_index] + [drawn]
        temp_winning = self.check_winning_hand_with_melds_temp(self.player_index, temp_hand, is_tsumo=True)
        if temp_winning:
            print("🎉 플레이어 화료!")
            # 화료 시에는 뜬 패를 손패에 추가
            self.hands[self.player_index].append(drawn)
            self.drawn_tile = None
            self.player_waiting = False
            self.game_winner = self.player_index
            self.finish_game("tsumo", self.player_index)
            return
        
        # 패를 뽑은 후 간방 상태 체크 (엎어 상태가 아닐 때만)
        if not self.player_riichi:
            self.check_and_show_tenpai_dialog_with_drawn_tile(self.player_index, drawn)
        
        # 자신의 턴에 가능한 액션 체크 (암깡, 가깡만 - 리치는 패를 버린 후)
        self_actions = []
        if self.drawn_tile:
            # 암깡 체크 (엎어 상태에서도 가능)
            available_an_gang = self.can_an_gang(self.player_index)
            if available_an_gang:
                self_actions.append({'type': 'an_gang', 'tiles': available_an_gang})
            
            # 가깡 체크 (엎어 상태에서도 가능)
            available_jia_gang = self.can_jia_gang(self.player_index, self.drawn_tile)
            if available_jia_gang:
                self_actions.append({'type': 'jia_gang', 'tiles': available_jia_gang})
        
        if self_actions:
            print(f"🎯 플레이어 액션 가능: {self_actions}")
            self.show_action_choice_ui(self_actions, None)
        else:
            # 플레이어 입력 대기
            self.waiting_for_player = True
            print("👤 패를 선택해서 버리세요")

    def start_ai_turn(self):
        """AI 턴 시작"""
        ai_name = self.player_names[self.current_turn]
        print(f"🤖 {ai_name} 턴 시작")
        
        # 현재 손패 수와 멜드 수 확인
        current_hand_size = len(self.hands[self.current_turn])
        meld_count = len(self.melds[self.current_turn])
        
        print(f"🎯 {ai_name} 상태: 손패={current_hand_size}장, 멜드={meld_count}개")
        
        # 멜드를 고려한 예상 손패 수 계산
        expected_hand_size_for_discard = 14 - (meld_count * 3)  # 패를 버려야 하는 상태
        expected_hand_size_for_draw = 13 - (meld_count * 3)     # 패를 뽑아야 하는 상태
        
        # 첫 턴 체크 (배패 직후 14장) 또는 펑/깡 후 패 버리기 상태
        if current_hand_size == expected_hand_size_for_discard:
            if meld_count == 0:
                print("🎯 AI 첫 턴: 14장에서 1장 버리기")
            else:
                print(f"🎯 AI 펑/깡 후: {current_hand_size}장에서 1장 버리기")
            
            # 자기 턴 액션 체크 (암깡, 가깡)
            self_actions = self.get_available_actions(self.current_turn, None, is_self_turn=True)
            if self_actions:
                # AI가 액션을 선택 (간단하게 첫 번째 액션 선택)
                action = self_actions[0]
                print(f"🤖 {ai_name}이 {action['type']} 실행")
                
                if action['type'] == 'an_gang':
                    # 암깡 실행 - tiles 배열에서 첫 번째 타일 사용
                    if 'tiles' in action and action['tiles']:
                        self.execute_gang(self.current_turn, action['type'], action['tiles'][0])
                    else:
                        print(f"❌ 암깡 타일 정보가 없음: {action}")
                        self.ai_discard_and_continue()
                elif action['type'] == 'jia_gang':
                    # 가깡 실행 - tiles 배열에서 첫 번째 타일 사용
                    if 'tiles' in action and action['tiles']:
                        self.execute_gang(self.current_turn, action['type'], action['tiles'][0])
                    else:
                        print(f"❌ 가깡 타일 정보가 없음: {action}")
                        self.ai_discard_and_continue()
                else:
                    self.ai_discard_and_continue()
            else:
                self.ai_discard_and_continue()
            return
        
        # 일반 턴: 패 뽑기
        if current_hand_size == expected_hand_size_for_draw:
            drawn = self.draw_tile_from_wall()
            if drawn is None:
                print(f"🚫 패산이 비어서 유국!")
                self.game_winner = None
                self.finish_game("draw", None)
                return
                
            # 꽃패 처리 - 왕패에서 보충
            while is_flower_tile(drawn):
                print(f"🌸 꽃패 받음: {drawn}")
                self.flower_tiles[self.current_turn].append(drawn)
                
                # 왕패에서 보충
                replacement = self.draw_flower_replacement_tile()
                if replacement is None:
                    print("🚫 왕패도 비어서 유국!")
                    self.game_winner = None
                    self.finish_game("draw", None)
                    return
                drawn = replacement
                print(f"🎴 꽃패 보충패 (왕패에서): {drawn}")
            
            self.hands[self.current_turn].append(drawn)
            print(f"✅ {ai_name}이 {drawn} 뽑음")
            
            # 쯔모 체크
            if self.check_winning_hand_with_melds(self.current_turn, is_tsumo=True):
                print(f"🎉 {ai_name} 쯔모!")
                self.game_winner = self.current_turn
                self.finish_game("tsumo", self.current_turn)
                return
            
            # 자기 턴 액션 체크 (암깡, 가깡)
            self_actions = self.get_available_actions(self.current_turn, None, is_self_turn=True)
            if self_actions:
                # AI가 액션을 선택 (간단하게 첫 번째 액션 선택)
                action = self_actions[0]
                print(f"🤖 {ai_name}이 {action['type']} 실행")
                
                if action['type'] == 'an_gang':
                    # 암깡 실행 - tiles 배열에서 첫 번째 타일 사용
                    if 'tiles' in action and action['tiles']:
                        self.execute_gang(self.current_turn, action['type'], action['tiles'][0])
                    else:
                        print(f"❌ 암깡 타일 정보가 없음: {action}")
                        self.ai_discard_and_continue()
                elif action['type'] == 'jia_gang':
                    # 가깡 실행 - tiles 배열에서 첫 번째 타일 사용
                    if 'tiles' in action and action['tiles']:
                        self.execute_gang(self.current_turn, action['type'], action['tiles'][0])
                    else:
                        print(f"❌ 가깡 타일 정보가 없음: {action}")
                        self.ai_discard_and_continue()
                else:
                    self.ai_discard_and_continue()
            else:
                self.ai_discard_and_continue()
        else:
            print(f"❌ {ai_name} 손패 수 오류: {current_hand_size}장 (예상: {expected_hand_size_for_draw} 또는 {expected_hand_size_for_discard}장)")
            self.ai_discard_and_continue()

    def ai_discard_after_peng(self):
        """펑 후 AI 패 버리기 - 다른 플레이어 액션 체크 없이 다음 턴으로"""
        ai_name = self.player_names[self.current_turn]
        hand = self.hands[self.current_turn]
        if not hand:
            print(f"❌ {ai_name} 손패가 비어있음!")
            self.advance_turn()
            return
        
        discarded = ai_choose_discard(hand, self.current_turn)
        if discarded and discarded in hand:
            hand.remove(discarded)
            
            # 패 버리기 애니메이션 추가 (버림패 더미에는 애니메이션 완료 후 추가)
            ai_position = self.get_player_screen_position(self.current_turn)
            from_pos = self.get_ai_hand_position(self.current_turn)
            to_pos = self.get_discard_pile_next_position(self.current_turn)  # 정확한 다음 위치로
            self.add_discard_animation(discarded, from_pos, to_pos, self.current_turn)
            
            print(f"✅ {ai_name}가 {discarded} 버림 (펑 후)")
            
            # AI 손패 정렬 - 위치에 따라
            ai_position = self.get_player_screen_position(self.current_turn)
            self.hands[self.current_turn] = sort_hand_by_position(hand, ai_position)
            
            # 애니메이션 완료 후 버림패 더미에 추가하고 다음 턴으로 진행
            self.waiting_for_animation = True
            self.animation_callback = lambda: self.complete_ai_discard_after_peng(discarded)
        else:
            print(f"❌ {ai_name} 패 버리기 실패")
            self.advance_turn()

    def ai_discard_and_continue(self):
        """AI 패 버리기 후 다음 턴 진행"""
        ai_name = self.player_names[self.current_turn]
        hand = self.hands[self.current_turn]
        if not hand:
            print(f"❌ {ai_name} 손패가 비어있음!")
            self.advance_turn()
            return
        
        discarded = ai_choose_discard(hand, self.current_turn)
        if discarded and discarded in hand:
            hand.remove(discarded)
            
            # 패 버리기 애니메이션 추가 (버림패 더미에는 애니메이션 완료 후 추가)
            ai_position = self.get_player_screen_position(self.current_turn)
            from_pos = self.get_ai_hand_position(self.current_turn)
            to_pos = self.get_discard_pile_next_position(self.current_turn)  # 정확한 다음 위치로
            self.add_discard_animation(discarded, from_pos, to_pos, self.current_turn)
            
            print(f"✅ {ai_name}가 {discarded} 버림")
            
            # AI 손패 정렬 - 위치에 따라
            ai_position = self.get_player_screen_position(self.current_turn)
            self.hands[self.current_turn] = sort_hand_by_position(hand, ai_position)
            
            # 애니메이션 완료 후 버림패 더미에 추가하고 액션 체크하도록 설정
            self.waiting_for_animation = True
            self.animation_callback = lambda: self.complete_ai_discard(discarded)
        else:
            print(f"❌ {ai_name} 패 버리기 실패")
            self.advance_turn()
    
    def complete_ai_discard_after_peng(self, discarded_tile):
        """펑 후 AI 패 버리기 완료 처리 (애니메이션 후 호출) - 다른 플레이어 액션 체크 없이 다음 턴으로"""
        # 버림패 더미에 추가
        self.discard_piles[self.current_turn].append(discarded_tile)
        print(f"🎬 애니메이션 완료: {discarded_tile}이 버림패 더미에 추가됨 (펑 후)")
        
        # 펑 후에는 다른 플레이어 액션 체크 없이 바로 다음 턴으로 진행
        self.advance_turn()

    def complete_ai_discard(self, discarded_tile):
        """AI 패 버리기 완료 처리 (애니메이션 후 호출)"""
        # 버림패 더미에 추가
        self.discard_piles[self.current_turn].append(discarded_tile)
        print(f"🎬 애니메이션 완료: {discarded_tile}이 버림패 더미에 추가됨")
        
        # 액션 체크
        self.check_actions_after_discard(self.current_turn, discarded_tile)
    
    def get_ai_hand_position(self, player_idx):
        """AI 손패 위치 계산"""
        pos = self.get_player_screen_position(player_idx)
        if pos == 'top':
            return (TABLE_CENTER_X, 60)
        elif pos == 'right':
            return (SCREEN_WIDTH - 250, TABLE_CENTER_Y - 100)
        elif pos == 'left':
            return (210, TABLE_CENTER_Y - 100)
        else:
            return (TABLE_CENTER_X, SCREEN_HEIGHT - 150)
    
    def get_discard_pile_center(self, player_idx):
        """버림패 더미 중앙 위치 계산"""
        pos = self.get_player_screen_position(player_idx)
        if pos == 'top':
            return (TABLE_CENTER_X, TABLE_CENTER_Y - 188)
        elif pos == 'right':
            return (TABLE_CENTER_X + 120, TABLE_CENTER_Y - 24)
        elif pos == 'left':
            return (TABLE_CENTER_X - 168, TABLE_CENTER_Y - 24)
        else:
            return (TABLE_CENTER_X, TABLE_CENTER_Y + 92)

    def begin_first_turn(self):
        """첫 턴 시작 - 동가부터"""
        print(f"\n=== 게임 시작: 동가부터 시작 ===")
        self.current_turn = self.east_player  # 동가부터 시작
        print(f"동가: {self.player_names[self.east_player]} (인덱스: {self.east_player})")
        self.start_turn()
        
        # 화면 업데이트
        self.render()
        pygame.display.flip()
    
    def handle_click(self, pos):
        """마우스 클릭 처리"""
        # 간방 다이얼로그가 활성화된 경우
        if hasattr(self, 'tenpai_dialog_active') and self.tenpai_dialog_active:
            self.close_tenpai_dialog()
            return
            
        # 화료 다이얼로그가 활성화된 경우
        if self.winning_dialog_active:
            self.close_winning_dialog()
            return
        
        if self.game_phase == "finished":
            if self.current_game <= self.total_games:
                self.start_next_game()
            else:
                print("🏁 모든 게임이 완료되었습니다!")
            return
        
        # 주사위 phase 처리
        if self.phase == 'dice' or self.phase == 'wall_dice':
            self.handle_dice_input()
            return
        
        if self.game_phase != "playing":
            return
        
        # 애니메이션 대기 중일 때 클릭 무시
        if self.waiting_for_animation:
            print("🎬 애니메이션 진행 중, 클릭 무시")
            return
        
        # 액션 선택 UI가 활성화된 경우
        if self.pending_action == 'choice' and self.action_choices:
            if self.handle_action_choice_click(pos):
                return
        
        # 플레이어 턴이 아닌 경우 클릭 무시
        if self.current_turn != self.player_index or not self.waiting_for_player:
            print("❌ 플레이어 턴이 아니므로 클릭 무시")
            return
        
        # 클릭 버퍼에 추가 (최근 턴 시작 후의 클릭만 유효)
        current_time = pygame.time.get_ticks()
        if current_time - self.last_player_turn_time > 100:  # 100ms 후부터 유효
            self.handle_player_discard(pos)
        else:
            print("⏰ 턴 시작 직후 클릭 무시")
    
    def close_winning_dialog(self):
        """화료 다이얼로그 닫기"""
        self.winning_dialog_active = False
        
        # 실제 게임 종료 처리 진행
        self.complete_game_finish(self.winning_result_type, self.winning_player_idx)
        
        # 정보 초기화
        self.winning_yaku_info = None
        self.winning_player_idx = None
        self.winning_result_type = None

    def handle_player_discard(self, pos):
        """플레이어 패 버리기 - 개선된 클릭 처리"""
        print(f"\n👤 === 플레이어 패 버리기 시작 ===")
        
        # 첫 턴인지 확인 (14장을 가지고 있고 drawn_tile이 None)
        is_first_turn = (len(self.hands[self.player_index]) == 14 and self.drawn_tile is None)
        
        # 패 수 확인
        actual_hand_size = len(self.hands[self.player_index])
        flower_count = len(self.flower_tiles[self.player_index])
        
        print(f"🎯 패 수 체크: 손패={actual_hand_size}장, 첫턴={'예' if is_first_turn else '아니오'}, 꽃패={flower_count}장")
        
        # 패 수 검증 (멜드 고려) - 더 유연하게 처리
        meld_count = len(self.melds[self.player_index])
        
        # 기본적으로 13장이어야 하지만, 뽑은 패가 있으면 14장
        if self.drawn_tile and self.drawn_tile in self.hands[self.player_index]:
            expected_hand_size = 14 - (meld_count * 3)
        else:
            expected_hand_size = 13 - (meld_count * 3)
        
        # 손패에서 클릭된 패 찾기 - render_player_area와 완전히 동일한 로직 사용
        clicked_tile_pos = None
        discarded_tile = None
        
        # 렌더링과 완전히 동일한 위치 계산
        idx = self.player_index
        start_x = TABLE_CENTER_X - 300  # render_player_area와 동일하게 수정
        start_y = SCREEN_HEIGHT - 150
        tile_spacing = 50
        flower_spacing = 35
        meld_spacing = 35
        section_gap = 20
        
        current_x = start_x
        
        # 1. 꽃패 영역 건너뛰기
        player_flower_tiles = self.flower_tiles[idx]
        flower_count = len(player_flower_tiles)
        if flower_count > 0:
            current_x += flower_count * flower_spacing + section_gap
        
        # 2. 멜드 영역 건너뛰기
        melds = self.melds[idx]
        if melds:
            for meld in melds:
                meld_width = len(meld['tiles']) * meld_spacing
                current_x += meld_width + 10  # 멜드 간 10px 간격
            current_x += section_gap
        
        # 3. 손패 영역에서 클릭 체크 - 정렬된 손패와 원본 손패의 정확한 매핑
        sorted_hand = sort_hand_by_position(self.hands[self.player_index], 'bottom')
        
        # 정렬된 손패의 각 패에 대해 원본 손패에서의 인덱스를 미리 계산
        sorted_to_original_indices = []
        original_hand_copy = self.hands[self.player_index][:]  # 원본 손패 복사본
        
        print(f"🔍 원본 손패: {self.hands[self.player_index]}")
        print(f"🔍 정렬된 손패: {sorted_hand}")
        
        for sorted_tile in sorted_hand:
            # 원본 손패에서 해당 패의 첫 번째 인덱스 찾기
            for orig_idx, orig_tile in enumerate(original_hand_copy):
                if orig_tile == sorted_tile:
                    sorted_to_original_indices.append(orig_idx)
                    original_hand_copy[orig_idx] = None  # 중복 방지를 위해 None으로 마킹
                    break
        
        print(f"🔍 정렬->원본 인덱스 매핑: {sorted_to_original_indices}")
        
        # 클릭 체크
        print(f"🔍 클릭 위치: {pos}")
        for i, tile in enumerate(sorted_hand):
            tile_x = current_x + i * tile_spacing
            tile_rect = pygame.Rect(tile_x, start_y, TILE_SIZE[0], TILE_SIZE[1])
            print(f"🔍 패 {i}: {tile}, 위치=({tile_x}, {start_y}), 영역={tile_rect}")
            
            if tile_rect.collidepoint(pos):
                # 엎어 상태에서는 손패 클릭 불가 (받은 패만 버릴 수 있음)
                if self.player_riichi:
                    print(f"🚫 엎어 상태에서는 손패를 버릴 수 없습니다. 받은 패만 버리세요.")
                    return
                
                print(f"🎯 손패에서 클릭: 정렬된_인덱스={i}, 패={tile}")
                # 정렬된 인덱스에 해당하는 원본 인덱스 사용
                original_index = sorted_to_original_indices[i]
                discarded_tile = self.hands[self.player_index].pop(original_index)
                clicked_tile_pos = (tile_x + TILE_SIZE[0]//2, start_y + TILE_SIZE[1]//2)
                print(f"🎯 원본 손패에서 제거: 원본_인덱스={original_index}, 패={discarded_tile}")
                break
        
        # 4. 뽑은 패 영역에서 클릭 체크
        if not discarded_tile and self.drawn_tile and self.current_turn == idx:
            drawn_x = current_x + len(sorted_hand) * tile_spacing + 15
            drawn_rect = pygame.Rect(drawn_x, start_y, TILE_SIZE[0], TILE_SIZE[1])
            print(f"🔍 뽑은 패: {self.drawn_tile}, 위치=({drawn_x}, {start_y}), 영역={drawn_rect}")
            
            if drawn_rect.collidepoint(pos):
                print(f"🎯 뽑은 패 클릭: {self.drawn_tile}")
                discarded_tile = self.drawn_tile
                self.drawn_tile = None
                self.player_waiting = False
                clicked_tile_pos = (drawn_x + TILE_SIZE[0]//2, start_y + TILE_SIZE[1]//2)
        
        # 손패를 버렸을 때는 뜬 패를 손패에 추가 (일반 턴에서만)
        if (discarded_tile and discarded_tile != self.drawn_tile and self.drawn_tile and 
            not getattr(self, 'after_peng', False)):
            print(f"🎯 손패를 버렸으므로 뜬 패 {self.drawn_tile}를 손패에 추가")
            self.hands[self.player_index].append(self.drawn_tile)
            # 손패 정렬
            player_position = self.get_player_screen_position(self.player_index)
            self.hands[self.player_index] = sort_hand_by_position(self.hands[self.player_index], player_position)
            self.drawn_tile = None
            self.player_waiting = False
        elif getattr(self, 'after_peng', False):
            # 펑/깡 후에는 drawn_tile을 무조건 초기화 (추가하지 않음)
            if self.drawn_tile:
                print(f"🔧 펑/깡 후 패 버리기: 뽑은 패 {self.drawn_tile} 무시 (추가하지 않음)")
                self.drawn_tile = None
                self.player_waiting = False
        
        if discarded_tile:
            print(f"✅ 플레이어가 {discarded_tile} 버림")
            self.waiting_for_player = False
            
            # 패를 실제로 버릴 때만 클릭 소리 재생
            self.play_click_sound()
            
            # 패 버리기 애니메이션 추가 (버림패 더미에는 애니메이션 완료 후 추가)
            if clicked_tile_pos:
                to_pos = self.get_discard_pile_next_position(self.player_index)  # 정확한 다음 위치로
                self.add_discard_animation(discarded_tile, clicked_tile_pos, to_pos, self.player_index)
            
            # 애니메이션 완료 후 버림패 더미에 추가하고 액션 체크하도록 설정
            self.waiting_for_animation = True
            self.animation_callback = lambda: self.complete_player_discard(discarded_tile)
        else:
            print("❌ 클릭된 패 없음")
    
    def complete_player_discard(self, discarded_tile):
        """플레이어 패 버리기 완료 처리 (애니메이션 후 호출)"""
        # 버림패 더미에 추가
        self.discard_piles[self.player_index].append(discarded_tile)
        print(f"🎬 애니메이션 완료: {discarded_tile}이 버림패 더미에 추가됨")
        
        # 펑 후인지 확인
        if hasattr(self, 'after_peng') and self.after_peng:
            print("🎯 펑 후 패 버리기 - 다른 플레이어 액션 체크 없이 다음 턴으로")
            self.after_peng = False  # 플래그 초기화
            self.advance_turn()
        else:
            # 패를 버린 후 간방 상태 체크 및 다이얼로그 표시 (엎어 상태가 아닐 때만)
            if not self.player_riichi:
                tenpai_dialog_shown = self.check_and_show_tenpai_dialog(self.player_index)
            
            # 패를 버린 후 엎어 체크 (아직 엎어하지 않았고 간방 상태인 경우)
            if (not self.player_riichi and 
                self.can_riichi(self.player_index) and 
                self.player_index == self.current_turn):
                print("🎯 패를 버린 후 엎어 가능!")
                riichi_actions = [{'type': 'riichi'}]
                self.show_action_choice_ui(riichi_actions, None)
            else:
                # 일반적인 패 버리기 - 다른 플레이어 액션 체크
                self.check_actions_after_discard(self.player_index, discarded_tile)

    def render(self):
        """화면 렌더링"""
        self.screen.fill(COLORS["bg"])
        
        if self.phase == 'dice' or self.phase == 'wall_dice':
            self.render_dice_phase()
        elif self.phase == 'deal_anim':
            self.render_deal_anim_phase()
        elif self.phase == 'playing':
            self.render_game()
        elif self.phase == 'finished':
            self.render_game()
            # 게임 종료 메시지와 점수 표시
            self.render_game_finished_ui()
        
        pygame.display.flip()
    
    def render_dice_phase(self):
        """주사위 던지기 화면 렌더링"""
        # 배경 색칠
        self.screen.fill(COLORS["bg"])
        
        # 현재 주사위 단계에 따른 제목 표시
        if not hasattr(self, 'dice_step'):
            self.dice_step = 'east'
        
        # 상단 영역 (화면의 상단 50%) - 동가 결정
        upper_area_height = SCREEN_HEIGHT // 2
        
        if self.dice_step == 'east' or (hasattr(self, 'dice_results') and self.dice_results and self.dice_step != 'wall_only'):
            # 동가 결정 제목
            title_text = self.resources.render_text_with_emoji("[1단계] 동가 결정", "small", COLORS["highlight"])
            title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, 50))
            self.screen.blit(title_text, title_rect)
        
        # 하단 영역 (화면의 하단 50%) - 패산 위치 결정
        lower_area_start = upper_area_height
        
        if self.dice_step in ['wall', 'wall_only'] or hasattr(self, 'wall_dice_results'):
            # 패산 위치 결정 제목
            if self.dice_step == 'wall_only':
                wall_title_text = self.resources.render_text_with_emoji(f"[{self.current_game}판] 패산 시작 위치 결정", "medium", COLORS["highlight"])
                wall_title_rect = wall_title_text.get_rect(center=(SCREEN_WIDTH//2, 100))
            else:
                wall_title_text = self.resources.render_text_with_emoji("[2단계] 패산 시작 위치 결정", "small", COLORS["highlight"])
                wall_title_rect = wall_title_text.get_rect(center=(SCREEN_WIDTH//2, lower_area_start + 30))
            self.screen.blit(wall_title_text, wall_title_rect)
        
        # 동가 결정 주사위 결과 표시 (상단 영역) - wall_only일 때는 숨김
        if self.dice_results and (self.dice_step == 'east' or self.dice_step == 'wall' or self.dice_step == 'complete') and self.dice_step != 'wall_only':
            start_y = 80
            
            # 주사위 영역 배경 (회색 반투명)
            dice_area_width = 450
            dice_area_height = 220
            dice_area_x = SCREEN_WIDTH//2 - dice_area_width//2
            dice_area_y = start_y - 10
            dice_bg_surface = pygame.Surface((dice_area_width, dice_area_height))
            dice_bg_surface.set_alpha(128)
            dice_bg_surface.fill((200, 200, 200))
            self.screen.blit(dice_bg_surface, (dice_area_x, dice_area_y))
            
            # 주사위 크기와 간격 설정
            dice_size = 45
            dice_spacing = 10  # 주사위 간 간격
            row_height = 50   # 각 줄 높이
            left_margin = 20  # 왼쪽 여백
            
            for i, (dice1, dice2, total) in enumerate(self.dice_results):
                # 동가가 된 플레이어는 하이라이트
                color = COLORS["highlight"] if i == self.east_player else COLORS["text"]
                
                # 각 줄의 Y 위치 계산
                row_y = start_y + i * row_height
                
                # 첫 번째 주사위 (왼쪽)
                dice1_x = dice_area_x + left_margin
                dice1_y = row_y
                dice1_rect = pygame.Rect(dice1_x, dice1_y, dice_size, dice_size)
                
                # 두 번째 주사위 (첫 번째 주사위 오른쪽)
                dice2_x = dice1_x + dice_size + dice_spacing
                dice2_y = row_y
                dice2_rect = pygame.Rect(dice2_x, dice2_y, dice_size, dice_size)
                
                # 주사위 배경과 테두리 그리기
                pygame.draw.rect(self.screen, (255, 255, 255), dice1_rect)
                pygame.draw.rect(self.screen, (0, 0, 0), dice1_rect, 2)
                pygame.draw.rect(self.screen, (255, 255, 255), dice2_rect)
                pygame.draw.rect(self.screen, (0, 0, 0), dice2_rect, 2)
                
                # 주사위 점 그리기
                self.draw_dice_dots(dice1_rect, dice1)
                self.draw_dice_dots(dice2_rect, dice2)
                
                # 플레이어 이름을 주사위 오른쪽에 왼쪽 정렬로 표시
                player_name = self.player_names[i]
                name_text = self.resources.render_text_with_emoji(player_name, "small", color)
                name_x = dice2_x + dice_size + 20  # 두 번째 주사위 오른쪽에 여백을 두고
                name_y = row_y + (dice_size - name_text.get_height()) // 2  # 주사위 중앙에 맞춤
                self.screen.blit(name_text, (name_x, name_y))
                
                # 합계 표시 (플레이어 이름 오른쪽)
                total_text = f"= {total}"
                total_surface = self.resources.render_text_with_emoji(total_text, "small", color)
                total_x = name_x + name_text.get_width() + 15
                total_y = name_y
                self.screen.blit(total_surface, (total_x, total_y))
            
            # 동가 결정 결과 메시지 (주사위 영역 아래로 이동)
            if hasattr(self, 'east_player') and self.east_player is not None:
                result_text = f"[결과] {self.player_names[self.east_player]}이 동가가 되었습니다!"
                text = self.resources.render_text_with_emoji(result_text, "small", COLORS["highlight"])
                # 주사위 영역 아래로 충분히 내림 (4줄 * 50px + 여백 30px)
                text_rect = text.get_rect(center=(SCREEN_WIDTH//2, start_y + 4 * 50 + 30))
                self.screen.blit(text, text_rect)
        
        # 패산 주사위 결과 표시 (하단 영역)
        if hasattr(self, 'wall_dice_results') and (self.dice_step == 'wall' or self.dice_step == 'wall_only' or self.dice_step == 'complete'):
            dice1, dice2, total = self.wall_dice_results
            
            wall_text = f"패산 주사위: {dice1} + {dice2} = {total}"
            text = self.resources.render_text_with_emoji(wall_text, "small", COLORS["highlight"])
            
            if self.dice_step == 'wall_only':
                text_rect = text.get_rect(center=(SCREEN_WIDTH//2, 180))
                dice_y = 210
            else:
                text_rect = text.get_rect(center=(SCREEN_WIDTH//2, lower_area_start + 80))
                dice_y = lower_area_start + 110
                
            self.screen.blit(text, text_rect)
            
            # 패산 주사위 영역 배경 (회색 반투명)
            wall_dice_area_width = 200
            wall_dice_area_height = 120
            wall_dice_area_x = SCREEN_WIDTH//2 - wall_dice_area_width//2
            wall_dice_area_y = dice_y - 10
            wall_dice_bg_surface = pygame.Surface((wall_dice_area_width, wall_dice_area_height))
            wall_dice_bg_surface.set_alpha(128)
            wall_dice_bg_surface.fill((200, 200, 200))
            self.screen.blit(wall_dice_bg_surface, (wall_dice_area_x, wall_dice_area_y))
            
            # 패산 주사위 이미지 (동가 결정 주사위와 같은 크기) - 세로로 정렬
            dice_size = 50
            dice1_rect = pygame.Rect(SCREEN_WIDTH//2 - dice_size//2, dice_y, dice_size, dice_size)
            dice2_rect = pygame.Rect(SCREEN_WIDTH//2 - dice_size//2, dice_y + dice_size + 10, dice_size, dice_size)
            
            pygame.draw.rect(self.screen, (255, 255, 255), dice1_rect)
            pygame.draw.rect(self.screen, (0, 0, 0), dice1_rect, 2)
            pygame.draw.rect(self.screen, (255, 255, 255), dice2_rect)
            pygame.draw.rect(self.screen, (0, 0, 0), dice2_rect, 2)
            
            # 주사위 점 그리기
            self.draw_dice_dots(dice1_rect, dice1)
            self.draw_dice_dots(dice2_rect, dice2)
            
            # 패산 위치 결과 (주사위 아래로 충분히 내림)
            if hasattr(self, 'wall_start_position'):
                position_text = f"패산 시작: {self.wall_start_position}번 플레이어 앞"
                text = self.resources.render_text_with_emoji(position_text, "small", COLORS["text"])
                
                if self.dice_step == 'wall_only':
                    # 주사위 2개 높이 + 간격 + 여백 (50 + 10 + 50 + 40)
                    text_rect = text.get_rect(center=(SCREEN_WIDTH//2, dice_y + dice_size * 2 + 50))
                else:
                    # 하단 영역에서도 주사위 아래로 충분히 내림
                    text_rect = text.get_rect(center=(SCREEN_WIDTH//2, lower_area_start + 240))
                    
                self.screen.blit(text, text_rect)
        
        # 사용자 입력 안내 메시지 (하단)
        if hasattr(self, 'waiting_for_user_input') and self.waiting_for_user_input:
            if self.dice_step == 'east':
                instruction_text = "스페이스바 또는 마우스 클릭으로 패산 주사위 던지기"
            elif self.dice_step == 'wall' or self.dice_step == 'wall_only':
                instruction_text = "스페이스바 또는 마우스 클릭으로 게임 시작"
            else:
                instruction_text = "스페이스바 또는 마우스 클릭으로 계속"
                
            text = self.resources.render_text_with_emoji(instruction_text, "small", COLORS["highlight"])
            text_rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 50))
            self.screen.blit(text, text_rect)
    
    def draw_dice_dots(self, rect, number):
        """주사위 점 그리기"""
        dot_positions = {
            1: [(0.5, 0.5)],
            2: [(0.25, 0.25), (0.75, 0.75)],
            3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
            4: [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)],
            5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)],
            6: [(0.25, 0.25), (0.75, 0.25), (0.25, 0.5), (0.75, 0.5), (0.25, 0.75), (0.75, 0.75)]
        }
        
        if number in dot_positions:
            # 주사위 크기에 따라 점 크기 조정
            dot_radius = max(4, rect.width // 10)
            for x_ratio, y_ratio in dot_positions[number]:
                dot_x = rect.left + rect.width * x_ratio
                dot_y = rect.top + rect.height * y_ratio
                pygame.draw.circle(self.screen, (0, 0, 0), (int(dot_x), int(dot_y)), dot_radius)
    
    def render_deal_anim_phase(self):
        """패산 먼저 그림"""
        for pos in self.SCREENS:
            self.render_wall(pos)
        # 임시 손패/꽃패 표시
        for pos in self.SCREENS:
            idx = self.screen_to_player[pos]
            # 손패
            hand = self.temp_hands[idx]
            if not hand:
                continue
            if pos == 'bottom':
                start_x = TABLE_CENTER_X - 320
                start_y = SCREEN_HEIGHT - 150
                tile_spacing = TILE_SIZE[0]  # 패 간격 없애기 (패 폭만큼만)
                current_x = start_x
                for tile in hand:
                    tile_surface = self.resources.get_tile_surface(tile, TILE_SIZE)
                    self.screen.blit(tile_surface, (current_x, start_y))
                    current_x += tile_spacing
            else:
                # AI는 뒷면
                tile_width = TILE_SIZE_DISCARD[0]
                tile_height = TILE_SIZE_DISCARD[1]
                if pos == 'top':
                    x, y, horizontal, rotation = TABLE_CENTER_X - 250, 60, True, 180
                elif pos == 'right':
                    x, y, horizontal, rotation = SCREEN_WIDTH - 250, TABLE_CENTER_Y - 150 - (tile_width * 2) - 40, False, 90
                elif pos == 'left':
                    x, y, horizontal, rotation = 210, TABLE_CENTER_Y - 150 - (tile_width * 2) - 40, False, -90
                else:
                    continue
                spacing = tile_width + 1  # AI 패 간격 1픽셀
                for i, _ in enumerate(hand):
                    if horizontal:
                        tile_x = x + i * spacing
                        tile_y = y
                    else:
                        tile_x = x
                        tile_y = y + i * spacing
                    back_surface = self.create_ai_back_surface(TILE_SIZE_DISCARD)
                    if rotation != 0:
                        back_surface = pygame.transform.rotate(back_surface, rotation)
                    self.screen.blit(back_surface, (tile_x, tile_y))

    def render_other_players(self):
        tile_width = TILE_SIZE_DISCARD[0]
        tile_height = TILE_SIZE_DISCARD[1]
        positions = {
            "top":    (TABLE_CENTER_X - 250, 60, True, 180),
            "right":  (SCREEN_WIDTH - 250, TABLE_CENTER_Y - 150 - (tile_width * 2) - 40, False, 90),
            "bottom": (TABLE_CENTER_X - 320, SCREEN_HEIGHT - 150, True, 0),
            "left":   (210, TABLE_CENTER_Y - 150 - (tile_width * 2) - 40, False, -90)
        }
        for screen_pos, (x, y, horizontal, rotation) in positions.items():
            if screen_pos == "bottom":
                self.render_player()
            else:
                player_idx = self.screen_to_player[screen_pos]
                if player_idx is not None and player_idx != self.player_index:
                    self.render_ai_player(player_idx, x, y, horizontal, rotation)

    def render_game(self):
        """게임 화면 렌더링 - 전통적인 마작 테이블 스타일"""
        for pos in self.SCREENS:
            self.render_wall(pos)
        for pos in ['left', 'top', 'right']:
            self.render_ai_area(pos)
        self.render_player_area()
        for pos in self.SCREENS:
            self.render_discard_pile(pos)
        self.render_info_panel()
        
        # 패 버리기 애니메이션 렌더링
        self.render_discard_animations()
        
        # 패 하이라이트 렌더링
        self.discard_manager.render_tile_highlights(self.discard_piles, self.screen_to_player)
        
        # 액션 선택 UI 렌더링
        if self.pending_action == 'choice' and self.action_choices:
            self.render_action_choice_ui()
        
        # 화료 다이얼로그 렌더링
        if self.winning_dialog_active:
            self.render_winning_dialog()
        
        # 간방 다이얼로그 렌더링
        if hasattr(self, 'tenpai_dialog_active') and self.tenpai_dialog_active:
            self.render_tenpai_dialog()
    
    def render_wall(self, pos):
        # WallManager를 사용하여 패산 렌더링
        if hasattr(self, 'wall_manager') and self.wall_manager:
            # 플레이어 방향 정보 생성
            directions = ['동', '남', '서', '북']  # 시계방향 순서
            screen_positions = ['bottom', 'right', 'top', 'left']  # 시계방향 화면 순서
            player_directions = {}
            
            for i, screen_pos in enumerate(screen_positions):
                player_idx = i
                relative_pos = (player_idx - self.east_player) % 4
                direction = directions[relative_pos]
                player_directions[screen_pos] = direction
            
            self.wall_manager.render_wall(player_directions)

    def get_wall_tile_global_index(self, pos, stack_idx, layer):
        # 시계방향(동→북→서→남)으로 패산 인덱스 계산
        stacks_per_side = 13
        tiles_per_stack = 2
        pos_order = ['bottom', 'left', 'top', 'right']  # 시계방향 순서
        side_index = pos_order.index(pos)
        return (side_index * stacks_per_side + stack_idx) * tiles_per_stack + layer

    def _get_wall_color(self, color_index):
        """패산 색상 반환"""
        wall_colors = [
            (100, 50, 50),    # 어두운 적색
            (50, 100, 50),    # 어두운 녹색
            (50, 50, 100),    # 어두운 청색
            (100, 100, 50),   # 어두운 황색
            (100, 50, 100),   # 어두운 자색
            (50, 100, 100),   # 어두운 청록색
        ]
        return wall_colors[color_index]
    
    def get_wall_tile_position(self, tile_index):
        """패산에서 특정 타일의 화면 위치 반환 (나중에 패 뽑기용)"""
        # 타일 인덱스를 기반으로 어느 면의 몇 번째 스택, 몇 층인지 계산
        tiles_per_stack = 2
        stacks_per_side = 13
        tiles_per_side = stacks_per_side * tiles_per_stack
        
        side_index = tile_index // tiles_per_side
        side_tile_index = tile_index % tiles_per_side
        stack_index = side_tile_index // tiles_per_stack
        layer = side_tile_index % tiles_per_stack
        
        # 동남서북 → 화면 위치 매핑
        direction_to_screen = {
            0: "bottom",  # 동가
            1: "left",   # 남가  
            2: "top",     # 서가
            3: "right"     # 북가
        }
        
        screen_pos = direction_to_screen[side_index]
        
        # 해당 위치의 좌표 계산 (render_wall과 동일한 로직)
        wall_tile_size = TILE_SIZE_DISCARD
        
        if screen_pos == "bottom":
            start_x = TABLE_CENTER_X - (stacks_per_side * (wall_tile_size[0] + 1)) // 2
            start_y = SCREEN_HEIGHT - 220  # 플레이어 패와 버림패 사이
            tile_x = start_x + stack_index * (wall_tile_size[0] + 1) - layer * 2
            tile_y = start_y - layer * 4
            
        elif screen_pos == "right":
            start_x = SCREEN_WIDTH - 280 - wall_tile_size[1]  # 좌측과 대칭으로 조정
            start_y = TABLE_CENTER_Y - (stacks_per_side * (wall_tile_size[0] + 1)) // 2
            tile_x = start_x - layer * 2
            tile_y = start_y + stack_index * (wall_tile_size[0] + 1) - layer * 4
            
        elif screen_pos == "top":
            start_x = TABLE_CENTER_X - (stacks_per_side * (wall_tile_size[0] + 1)) // 2
            start_y = 120  # AI 패와 버림패 사이
            tile_x = start_x + stack_index * (wall_tile_size[0] + 1) - layer * 2
            tile_y = start_y - layer * 4
            
        elif screen_pos == "left":
            start_x = 280  # 기준 위치 유지
            start_y = TABLE_CENTER_Y - (stacks_per_side * (wall_tile_size[0] + 1)) // 2
            tile_x = start_x - layer * 2
            tile_y = start_y + stack_index * (wall_tile_size[0] + 1) - layer * 4
        
        return tile_x, tile_y, screen_pos
    
    def render_discard_pile(self, pos):
        """버림패 렌더링 - DiscardManager 사용"""
        self.discard_manager.render_discard_pile(pos, self.discard_piles, self.screen_to_player)
    
    def render_player_area(self):
        idx = self.player_index
        start_x = TABLE_CENTER_X - 300  # 좌우 대칭을 위해 중앙에 더 가깝게 조정
        start_y = SCREEN_HEIGHT - 150
        tile_spacing = 50
        flower_spacing = 35  # 꽃패 간격
        meld_spacing = 35    # 멜드 내 패 간격
        section_gap = 20     # 섹션 간 간격
        
        current_x = start_x
        
        # 1. 꽃패 렌더링 (가장 왼쪽)
        player_flower_tiles = self.flower_tiles[idx]
        flower_count = len(player_flower_tiles)
        if flower_count > 0:
            for i in range(flower_count):
                flower_surface = self.resources.get_tile_surface(player_flower_tiles[i], TILE_SIZE)
                self.screen.blit(flower_surface, (current_x, start_y))
                current_x += flower_spacing
            
            # 꽃패와 멜드 사이 간격
            current_x += section_gap
        
        # 2. 멜드 렌더링 (꽃패 다음)
        melds = self.melds[idx]
        if melds:
            for i, meld in enumerate(melds):
                # 각 멜드의 패들을 가로로 배치
                for j, tile in enumerate(meld['tiles']):
                    # 암깡의 경우 첫째(0)와 네째(3) 패만 보여주고, 둘째(1)와 세째(2)는 뒷면
                    if meld['type'] == 'an_gang' and j in [1, 2]:
                        # 뒷면 렌더링
                        back_surface = self.create_ai_back_surface(TILE_SIZE)
                        self.screen.blit(back_surface, (current_x + j * meld_spacing, start_y))
                    else:
                        # 일반 패 렌더링
                        tile_surface = self.resources.get_tile_surface(tile, TILE_SIZE)
                        self.screen.blit(tile_surface, (current_x + j * meld_spacing, start_y))
                
                # 멜드 타입 표시 (패 위쪽)
                meld_type_text = {'peng': '펑', 'ming_gang': '명깡', 'an_gang': '암깡', 'jia_gang': '가깡'}.get(meld['type'], meld['type'])
                type_surface = self.resources.render_text_with_emoji(meld_type_text, "small", COLORS["highlight"])
                self.screen.blit(type_surface, (current_x, start_y - 20))
                
                # 다음 멜드 위치 계산
                meld_width = len(meld['tiles']) * meld_spacing
                current_x += meld_width + 10  # 멜드 간 10px 간격
            
            # 멜드와 손패 사이 간격
            current_x += section_gap
        
        # 3. 손패 렌더링 (정렬된 순서로)
        sorted_hand = sort_hand_by_position(self.hands[idx], 'bottom')
        for tile in sorted_hand:
            tile_surface = self.resources.get_tile_surface(tile, TILE_SIZE)
            self.screen.blit(tile_surface, (current_x, start_y))
            current_x += tile_spacing
            
        # 4. 뽑은 패 렌더링 (15픽셀 간격)
        if self.drawn_tile and self.current_turn == idx:
            drawn_x = current_x + 15
            drawn_surface = self.resources.get_tile_surface(self.drawn_tile, TILE_SIZE)
            self.screen.blit(drawn_surface, (drawn_x, start_y))
        
        # 정보 텍스트
        total_tiles = len(self.hands[idx]) + (1 if self.drawn_tile and self.current_turn == idx else 0)
        meld_count = len(self.melds[idx])
        info_text = f"{self.player_names[idx]} - {total_tiles}장"
        if flower_count > 0:
            info_text += f" + 꽃패 {flower_count}장"
        if meld_count > 0:
            info_text += f" + 멜드 {meld_count}개"
        
        # 엎어 상태 표시
        if self.player_riichi:
            info_text += " [엎어]"
        
        info_surface = self.resources.render_text_with_emoji(info_text, "small", COLORS["text"])
        info_x = TABLE_CENTER_X - info_surface.get_width() // 2
        info_y = start_y + TILE_SIZE[1] + 5
        self.screen.blit(info_surface, (info_x, info_y))
        
        # 간방 상태 대기패 표시 (왼쪽 아래에 지속적으로 표시) - 엎어 상태에서도 표시
        # 간방 상태는 엎어 여부와 관계없이 체크 (대기패 표시용)
        current_tenpai_state = self.is_tenpai(self.player_index)
        current_waiting_tiles = []
        
        if current_tenpai_state:
            current_waiting_tiles = self.get_winning_hints(self.player_index)
            # 상태 업데이트 (다이얼로그 표시하지 않고)
            self.player_tenpai_state = True
            self.tenpai_waiting_tiles = current_waiting_tiles
        
        if (self.game_phase == "playing" and 
            current_tenpai_state and current_waiting_tiles):  # 엎어 상태에서도 대기패 표시
            
            waiting_tiles = current_waiting_tiles
            # 간방 상태 대기패를 왼쪽 아래 구석에 표시
            hint_area_x = 20  # 왼쪽 여백
            hint_area_y = SCREEN_HEIGHT - 120  # 아래쪽 여백
            
            # 힌트 개수에 따라 배경 크기 동적 조정
            hint_count = len(waiting_tiles)
            tile_size = TILE_SIZE_DISCARD  # (36, 54) AI 패 크기 사용
            tile_spacing = 30  # 패 간격
            
            # 기본 크기 (3개 패 기준)
            base_width = 3 * tile_size[0] + 2 * tile_spacing + 20  # 패 3개 + 간격 + 여백
            base_height = tile_size[1] + 50  # 패 높이 + 텍스트 + 여백
            
            # 실제 필요한 크기 계산
            needed_width = hint_count * tile_size[0] + (hint_count - 1) * tile_spacing + 20
            actual_width = max(base_width, needed_width)  # 최소 3개 패 크기 보장
            actual_height = base_height
            
            # 간방 상태 배경 (엎어 상태에 따라 색상 변경) - 동적 크기
            hint_bg_surface = pygame.Surface((actual_width, actual_height))
            hint_bg_surface.set_alpha(180)
            if self.player_riichi:
                hint_bg_surface.fill((60, 40, 20))  # 어두운 금색 (엎어 상태)
            else:
                hint_bg_surface.fill((20, 60, 20))  # 어두운 녹색 (일반 간방)
            self.screen.blit(hint_bg_surface, (hint_area_x, hint_area_y))
            
            # 간방 상태 텍스트 (엎어 상태 고려)
            if self.player_riichi:
                hint_text = f"[엎어] 대기패: {hint_count}개"
                hint_color = (255, 215, 0)  # 금색 (엎어 상태)
            elif hasattr(self, 'tenpai_options') and self.tenpai_options:
                best_option = self.tenpai_options[0]  # 가장 좋은 옵션 (대기패 많은 순)
                hint_text = f"[간방] {best_option['discard_name']} 버리기 → {hint_count}개 대기"
                hint_color = (100, 255, 100)  # 밝은 녹색 (일반 간방)
            else:
                hint_text = f"[간방] 대기패: {hint_count}개"
                hint_color = (100, 255, 100)  # 밝은 녹색 (일반 간방)
            
            hint_surface = self.resources.render_text_with_emoji(hint_text, "small", hint_color)
            hint_x = hint_area_x + 10
            hint_y = hint_area_y + 10
            self.screen.blit(hint_surface, (hint_x, hint_y))
            
            # 대기패들을 실제 마작패 이미지로 표시
            if hint_count <= 12:  # 최대 12개까지 표시
                hint_tiles_x = hint_area_x + 10
                hint_tiles_y = hint_y + 25
                
                for i, hint_tile in enumerate(waiting_tiles):
                    # AI 패 크기로 마작패 이미지 렌더링
                    tile_surface = self.resources.get_tile_surface(hint_tile, tile_size)
                    tile_x = hint_tiles_x + i * tile_spacing
                    self.screen.blit(tile_surface, (tile_x, hint_tiles_y))
        
        # 기존 화료 힌트 표시 (간방 상태가 아닐 때만)
        elif (self.current_turn == self.player_index and 
              self.game_phase == "playing" and 
              self.waiting_for_player and
              not getattr(self, 'player_tenpai_state', False)):
            
            winning_hints = self.get_winning_hints(self.player_index)
            if winning_hints:
                # 화료 힌트를 왼쪽 아래 구석에 표시 (위치 조정)
                hint_area_x = 20  # 왼쪽 여백 (50 → 20으로 더 왼쪽으로)
                hint_area_y = SCREEN_HEIGHT - 120  # 아래쪽 여백 (200 → 120으로 더 아래로)
                
                # 힌트 개수에 따라 배경 크기 동적 조정
                hint_count = len(winning_hints)
                tile_size = TILE_SIZE_DISCARD  # (36, 54) AI 패 크기 사용
                tile_spacing = 30  # 패 간격
                
                # 기본 크기 (3개 패 기준)
                base_width = 3 * tile_size[0] + 2 * tile_spacing + 20  # 패 3개 + 간격 + 여백
                base_height = tile_size[1] + 50  # 패 높이 + 텍스트 + 여백
                
                # 실제 필요한 크기 계산
                needed_width = hint_count * tile_size[0] + (hint_count - 1) * tile_spacing + 20
                actual_width = max(base_width, needed_width)  # 최소 3개 패 크기 보장
                actual_height = base_height
                
                # 화료 힌트 배경 (반투명) - 동적 크기
                hint_bg_surface = pygame.Surface((actual_width, actual_height))
                hint_bg_surface.set_alpha(180)
                hint_bg_surface.fill((40, 40, 40))
                self.screen.blit(hint_bg_surface, (hint_area_x, hint_area_y))
                
                # 화료 힌트 텍스트
                hint_text = f"화료 가능: {hint_count}개 패"
                hint_surface = self.resources.render_text_with_emoji(hint_text, "small", COLORS["highlight"])
                hint_x = hint_area_x + 10
                hint_y = hint_area_y + 10
                self.screen.blit(hint_surface, (hint_x, hint_y))
                
                # 화료 가능한 패들을 실제 마작패 이미지로 표시
                if hint_count <= 12:  # 최대 12개까지 표시
                    hint_tiles_x = hint_area_x + 10
                    hint_tiles_y = hint_y + 25
                    
                    for i, hint_tile in enumerate(winning_hints):
                        # AI 패 크기로 마작패 이미지 렌더링
                        tile_surface = self.resources.get_tile_surface(hint_tile, tile_size)
                        tile_x = hint_tiles_x + i * tile_spacing
                        self.screen.blit(tile_surface, (tile_x, hint_tiles_y))

    def render_ai_area(self, pos):
        idx = self.screen_to_player[pos]
        tile_width = TILE_SIZE_DISCARD[0]
        tile_height = TILE_SIZE_DISCARD[1]
        if pos == 'top':
            x, y, horizontal, rotation = TABLE_CENTER_X - 250, 60, True, 180
        elif pos == 'right':
            x, y, horizontal, rotation = SCREEN_WIDTH - 250, TABLE_CENTER_Y - 150 - (tile_width * 2) - 40, False, 90
        elif pos == 'left':
            x, y, horizontal, rotation = 210, TABLE_CENTER_Y - 150 - (tile_width * 2) - 40, False, -90
        else:
            return
        hand = self.hands[idx]
        game_finished = (self.game_phase == "finished")
        spacing = tile_width + 1  # AI 패 간격을 1픽셀로 설정
        flower_spacing = 25   # 꽃패 간격
        meld_spacing = 25     # 멜드 내 패 간격
        section_gap = 15      # 섹션 간 간격
        
        # 렌더링 순서: 꽃패 → 멜드 → 손패
        current_pos = 0  # 현재 렌더링 위치
        
        # 1. 꽃패 렌더링 (가장 먼저)
        flower_tiles = self.flower_tiles[idx]
        if flower_tiles:
            flower_count = len(flower_tiles)
            
            if pos == 'top':
                # 상단: 오른쪽에서 왼쪽으로
                for i, flower_tile in enumerate(flower_tiles):
                    flower_surface = self.resources.get_tile_surface(flower_tile, TILE_SIZE_DISCARD)
                    flower_surface = pygame.transform.rotate(flower_surface, 180)
                    self.screen.blit(flower_surface, (x + current_pos + i * flower_spacing, y))
                current_pos += flower_count * flower_spacing + section_gap
                
            elif pos == 'right':
                # 우측: 아래에서 위로
                for i, flower_tile in enumerate(flower_tiles):
                    flower_surface = self.resources.get_tile_surface(flower_tile, TILE_SIZE_DISCARD)
                    flower_surface = pygame.transform.rotate(flower_surface, 90)
                    self.screen.blit(flower_surface, (x, y + current_pos + i * flower_spacing))
                current_pos += flower_count * flower_spacing + section_gap
                
            elif pos == 'left':
                # 좌측: 위에서 아래로
                for i, flower_tile in enumerate(flower_tiles):
                    flower_surface = self.resources.get_tile_surface(flower_tile, TILE_SIZE_DISCARD)
                    flower_surface = pygame.transform.rotate(flower_surface, -90)
                    self.screen.blit(flower_surface, (x, y + current_pos + i * flower_spacing))
                current_pos += flower_count * flower_spacing + section_gap
        
        # 2. 멜드 렌더링
        melds = self.melds[idx]
        if melds:
            for i, meld in enumerate(melds):
                meld_size = len(meld['tiles'])
                
                if pos == 'top':
                    # 상단: 오른쪽에서 왼쪽으로
                    for j, tile in enumerate(meld['tiles']):
                        # 암깡의 경우 첫째(0)와 네째(3) 패만 보여주고, 둘째(1)와 세째(2)는 뒷면
                        if meld['type'] == 'an_gang' and j in [1, 2]:
                            # 뒷면 렌더링
                            back_surface = self.create_ai_back_surface(TILE_SIZE_DISCARD)
                            back_surface = pygame.transform.rotate(back_surface, 180)
                            self.screen.blit(back_surface, (x + current_pos + j * meld_spacing, y))
                        else:
                            # 일반 패 렌더링
                            tile_surface = self.resources.get_tile_surface(tile, TILE_SIZE_DISCARD)
                            tile_surface = pygame.transform.rotate(tile_surface, 180)
                            self.screen.blit(tile_surface, (x + current_pos + j * meld_spacing, y))
                    current_pos += meld_size * meld_spacing + 10  # 멜드 간 간격
                    
                elif pos == 'right':
                    # 우측: 아래에서 위로
                    for j, tile in enumerate(meld['tiles']):
                        # 암깡의 경우 첫째(0)와 네째(3) 패만 보여주고, 둘째(1)와 세째(2)는 뒷면
                        if meld['type'] == 'an_gang' and j in [1, 2]:
                            # 뒷면 렌더링
                            back_surface = self.create_ai_back_surface(TILE_SIZE_DISCARD)
                            back_surface = pygame.transform.rotate(back_surface, 90)
                            self.screen.blit(back_surface, (x, y + current_pos + j * meld_spacing))
                        else:
                            # 일반 패 렌더링
                            tile_surface = self.resources.get_tile_surface(tile, TILE_SIZE_DISCARD)
                            tile_surface = pygame.transform.rotate(tile_surface, 90)
                            self.screen.blit(tile_surface, (x, y + current_pos + j * meld_spacing))
                    current_pos += meld_size * meld_spacing + 10  # 멜드 간 간격
                    
                elif pos == 'left':
                    # 좌측: 위에서 아래로
                    for j, tile in enumerate(meld['tiles']):
                        # 암깡의 경우 첫째(0)와 네째(3) 패만 보여주고, 둘째(1)와 세째(2)는 뒷면
                        if meld['type'] == 'an_gang' and j in [1, 2]:
                            # 뒷면 렌더링
                            back_surface = self.create_ai_back_surface(TILE_SIZE_DISCARD)
                            back_surface = pygame.transform.rotate(back_surface, -90)
                            self.screen.blit(back_surface, (x, y + current_pos + j * meld_spacing))
                        else:
                            # 일반 패 렌더링
                            tile_surface = self.resources.get_tile_surface(tile, TILE_SIZE_DISCARD)
                            tile_surface = pygame.transform.rotate(tile_surface, -90)
                            self.screen.blit(tile_surface, (x, y + current_pos + j * meld_spacing))
                    current_pos += meld_size * meld_spacing + 10  # 멜드 간 간격
            
            # 멜드와 손패 사이 간격 추가
            current_pos += section_gap
        # 3. 손패 렌더링 (정렬된 순서로)
        sorted_hand = sort_hand_by_position(hand, pos)
        
        for i, tile in enumerate(sorted_hand):
            if pos == 'top':
                # 상단: 오른쪽에서 왼쪽으로 배치
                tile_x = x + current_pos + i * spacing
                tile_y = y
            elif pos == 'right':
                # 우측: 아래에서 위로 배치
                tile_x = x
                tile_y = y + current_pos + i * spacing
            elif pos == 'left':
                # 좌측: 위에서 아래로 배치
                tile_x = x
                tile_y = y + current_pos + i * spacing
            else:
                # 기본값 (하단 플레이어)
                tile_x = x + current_pos + i * spacing
                tile_y = y
            if game_finished:
                tile_surface = self.resources.get_tile_surface(tile, TILE_SIZE_DISCARD)
                if rotation != 0:
                    tile_surface = pygame.transform.rotate(tile_surface, rotation)
                self.screen.blit(tile_surface, (tile_x, tile_y))
            else:
                back_surface = self.create_ai_back_surface(TILE_SIZE_DISCARD)
                if rotation != 0:
                    back_surface = pygame.transform.rotate(back_surface, rotation)
                self.screen.blit(back_surface, (tile_x, tile_y))
        # 플레이어 정보 텍스트 (상단은 한 줄, 좌우는 두 줄)
        flower_count = len(self.flower_tiles[idx])
        meld_count = len(self.melds[idx])
        name = self.player_names[idx]
        player_type = self.players[idx]
        
        if pos == 'top':
            # 상단 플레이어는 한 줄로 표시
            info_text = f"{name}({player_type}) {len(hand)}장"
            if flower_count > 0:
                info_text += f" + 꽃패 {flower_count}장"
            if meld_count > 0:
                info_text += f" + 멜드 {meld_count}개"
            if game_finished:
                info_text += " [패 공개]"
            info_surface = self.resources.render_text_with_emoji(info_text, "small", COLORS["text"])
            info_x = x
            info_y = y - 25
            self.screen.blit(info_surface, (info_x, info_y))
        else:
            # 좌우 플레이어는 두 줄로 표시
            line1 = f"{name}({player_type})"
            line2 = f"{len(hand)}장"
            if flower_count > 0:
                line2 += f" + 꽃패 {flower_count}장"
            if meld_count > 0:
                line2 += f" + 멜드 {meld_count}개"
            if game_finished:
                line2 += " [패 공개]"
            info_surfaces = [self.resources.render_text_with_emoji(line1, "small", COLORS["text"]),
                             self.resources.render_text_with_emoji(line2, "small", COLORS["text"])]
            
            if pos == 'left':
                info_x = x - info_surfaces[0].get_width() - 20
                info_y = y
            else:  # pos == 'right'
                info_x = x + tile_height + 20
                info_y = y
            
            for j, surface in enumerate(info_surfaces):
                self.screen.blit(surface, (info_x, info_y + j * 18))
    
    def create_ai_back_surface(self, size):
        """AI 플레이어용 패 뒷면 생성"""
        # 통일된 어두운 청색 뒷면
        back_color = (40, 40, 80)
        
        # 색깔이 있는 직사각형으로 패 뒷면 그리기
        surface = pygame.Surface(size)
        surface.fill(back_color)
        pygame.draw.rect(surface, (20, 20, 20), surface.get_rect(), 2)  # 테두리
        
        # 통일된 점 패턴
        for row in range(2):
            for col in range(3):
                dot_x = 6 + col * 8
                dot_y = 8 + row * 16
                pygame.draw.circle(surface, (200, 200, 200), (dot_x, dot_y), 2)
        
        return surface
    
    def render_info_panel(self):
        """정보 패널 렌더링"""
        # 현재 턴 표시
        current_name = self.player_names[self.current_turn]
        turn_text = f"현재 턴: {current_name} [#{self.current_turn}]"
        
        # 남은 패 수
        remaining_text = f"남은 패: {self.wall_manager.get_remaining_tiles_count()}장"
        
        # 턴 카운터
        turn_counter_text = f"총 턴: {self.turn_counter}"
        
        # 게임 진행 상황
        game_progress_text = f"게임: {self.current_game}/{self.total_games}판"
        
        # 플레이어 상태
        if self.current_turn == self.player_index:
            if self.waiting_for_player:
                status_text = "[플레이어] 입력 대기중"
            else:
                status_text = "[플레이어] 처리중"
        else:
            status_text = "[AI] 처리중"
        
        # 정보 표시
        info_x = 20
        info_y = 20
        
        texts = [turn_text, remaining_text, turn_counter_text, game_progress_text, status_text]
        for i, text in enumerate(texts):
            color = COLORS["highlight"] if i == 0 else COLORS["text"]
            info_surface = self.resources.render_text_with_emoji(text, "small", color)
            self.screen.blit(info_surface, (info_x, info_y + i * 25))
        
        # 플레이어 점수 표시 (오른쪽 상단)
        score_x = SCREEN_WIDTH - 200
        score_y = 20
        
        # 제목
        score_title = self.resources.render_text_with_emoji("현재 점수", "medium", COLORS["highlight"])
        self.screen.blit(score_title, (score_x, score_y))
        
        # 각 플레이어 점수
        for i, (name, score) in enumerate(zip(self.player_names, self.player_scores)):
            y_pos = score_y + 35 + i * 25
            
            # 현재 턴인 플레이어는 하이라이트
            if i == self.current_turn:
                color = COLORS["highlight"]
                prefix = "▶ "
            else:
                color = COLORS["text"]
                prefix = "   "
            
            # 리치 상태 표시
            riichi_status = ""
            if i == self.player_index and self.player_riichi:
                riichi_status = " [리치]"
            
            score_text = f"{prefix}{name}: {score}점{riichi_status}"
            score_surface = self.resources.render_text_with_emoji(score_text, "small", color)
            self.screen.blit(score_surface, (score_x, y_pos))

    def update(self):
        """게임 상태 업데이트"""
        # 배패 애니메이션 업데이트
        if self.phase == 'deal_anim':
            self.update_deal_anim()
        
        # 패 버리기 애니메이션 업데이트
        self.update_discard_animations()
        
        # 예약된 페이즈 체크
        self.check_scheduled_phase()
        
        # 게임 상태 모니터링
        current_time = pygame.time.get_ticks()
        if not hasattr(self, 'last_debug_time'):
            self.last_debug_time = 0
        
        if current_time - self.last_debug_time > 10000:  # 10초마다
            print(f"🔄 === 게임 상태 (10초마다) ===")
            print(f"게임단계: {self.game_phase}")
            if hasattr(self, 'player_names') and len(self.player_names) > self.current_turn:
                print(f"현재턴: {self.current_turn} ({self.player_names[self.current_turn]})")
            print(f"플레이어 대기중: {self.waiting_for_player}")
            print(f"뽑은패: {self.drawn_tile}")
            print(f"총 턴 수: {self.turn_counter}")
            print(f"패산: {self.wall_manager.get_remaining_tiles_count()}장 남음")
            if hasattr(self, 'hands') and hasattr(self, 'player_names'):
                for i in range(min(4, len(self.hands), len(self.player_names))):
                    print(f"  {self.player_names[i]}: 손패 {len(self.hands[i])}장, 버림패 {len(self.discard_piles[i])}장")
            print(f"=== 게임 상태 끝 ===\n")
            self.last_debug_time = current_time
    
    def update_deal_anim(self):
        now = pygame.time.get_ticks()
        if now - self.deal_anim_last_time < 120:
            return
        print(f"[DEBUG] deal_anim_index={self.deal_anim_index}, temp_deal_order_len={len(self.temp_deal_order)}, wall_tiles_len={len(self.wall_tiles)}, dealt_tiles_len={len(self.wall_manager.dealt_tiles)}")
        if self.deal_anim_index >= len(self.temp_deal_order):
            print('[DEBUG] 패 배분 완료:', [len(h) for h in self.temp_hands], '패산:', self.wall_manager.get_remaining_tiles_count())
            
            # 배패 결과를 실제 게임 상태로 복사
            self.hands = [h[:] for h in self.temp_hands]
            self.flower_tiles = [f[:] for f in self.temp_flower_tiles]
            
            # 패산 관리는 WallManager에 완전히 위임됨
            
            # 손패 정렬 - 각 플레이어 위치에 따라
            for i in range(4):
                player_position = self.get_player_screen_position(i)
                self.hands[i] = sort_hand_by_position(self.hands[i], player_position)
            
            # 배패 완료 정보 출력
            print("\n=== 배패 완료! ===")
            for i, (name, hand) in enumerate(zip(self.player_names, self.hands)):
                flower_count = len(self.flower_tiles[i])
                print(f"{name}: {len(hand)}장 + 꽃패 {flower_count}장")
            
            # 게임 시작
            self.phase = 'playing'
            self.game_phase = 'playing'
            self.begin_first_turn()
            return

        player_idx = self.temp_deal_order[self.deal_anim_index]
        
        # WallManager를 사용하여 패산에서 패 뽑기
        result = self.wall_manager.draw_regular_tile()
        print(f"[DEBUG] 배분: player_idx={player_idx}, WallManager 결과={result}")
        
        if result is not None:
            tile, tile_index = result
            
            # 꽃패 처리 - 보충패 뽑기 포함
            if is_flower_tile(tile):
                print(f"🌸 배패 중 꽃패 받음: {tile} (플레이어 {player_idx})")
                self.temp_flower_tiles[player_idx].append(tile)
                
                # 꽃패 보충패 뽑기 - WallManager 사용하여 왕패에서 뽑기
                attempts = 0
                while attempts < 3:
                    replacement_result = self.wall_manager.draw_wang_tile()
                    if replacement_result is not None:
                        replacement_tile, replacement_index = replacement_result
                        
                        if not is_flower_tile(replacement_tile):
                            # 일반 패면 손패에 추가
                            self.temp_hands[player_idx].append(replacement_tile)
                            print(f"🎴 꽃패 보충패 (왕패에서): {replacement_tile}")
                            break
                        else:
                            # 또 꽃패면 꽃패 더미에 추가하고 다시 시도
                            self.temp_flower_tiles[player_idx].append(replacement_tile)
                            print(f"🌸 보충패도 꽃패 (왕패에서): {replacement_tile}")
                    else:
                        print(f"⚠️ 왕패에서 보충패를 뽑을 수 없음")
                        break
                    attempts += 1
                    
                if attempts >= 3:
                    print(f"⚠️ 꽃패 보충 시도 3회 초과, 강제 종료")
            else:
                self.temp_hands[player_idx].append(tile)
        
        self.deal_anim_index += 1
        self.deal_anim_last_time = now
    
    def get_flower_replacement_tile_index(self):
        """꽃패 보충용 왕패에서 패 인덱스 계산"""
        # 패산 구조: 4면 × 13스택 × 2층 = 104장
        # 인덱스 범위: bottom(0-25), left(26-51), top(52-77), right(78-103)
        # 
        # 일반 패 뽑기: 동가(bottom) 스택0부터 시계방향으로 진행
        # 왕패 뽑기: 북가(right) 스택12부터 시계 반대방향으로 진행
        
        # WallManager에서 이미 뽑힌 왕패 개수 가져오기
        flower_replacement_count = len(self.wall_manager.dealt_wang_tiles)
        
        # 왕패 순서대로 확인: 북가 스택12 → 북가 스택11 → ... → 동가 스택0
        wang_indices = self.get_all_wang_indices()
        
        # 다음에 뽑을 왕패 인덱스
        if flower_replacement_count >= len(wang_indices):
            print(f"⚠️ 왕패 범위 초과, 더 이상 꽃패 보충 불가")
            return None
            
        next_wang_index = wang_indices[flower_replacement_count]
        print(f"[DEBUG] 꽃패 보충 위치: 왕패 순서={flower_replacement_count}, 인덱스={next_wang_index}")
        return next_wang_index
    
    def get_all_wang_indices(self):
        """모든 왕패 인덱스를 순서대로 반환"""
        # 왕패는 일반 패 뽑기의 정반대 순서
        # 일반 패: 동가 스택0부터 시계방향 (bottom→left→top→right)
        # 왕패: 북가 스택12부터 시계 반대방향 (right→top→left→bottom)
        
        wang_indices = []
        
        # 북가(right) 패산: 스택 12→0, 각 스택에서 아래층→위층
        for stack in range(12, -1, -1):
            for layer in [0, 1]:  # 아래층부터
                index = self.get_wall_tile_global_index('right', stack, layer)
                wang_indices.append(index)
        
        # 서가(top) 패산: 스택 12→0, 각 스택에서 아래층→위층  
        for stack in range(12, -1, -1):
            for layer in [0, 1]:
                index = self.get_wall_tile_global_index('top', stack, layer)
                wang_indices.append(index)
        
        # 남가(left) 패산: 스택 12→0, 각 스택에서 아래층→위층
        for stack in range(12, -1, -1):
            for layer in [0, 1]:
                index = self.get_wall_tile_global_index('left', stack, layer)
                wang_indices.append(index)
        
        # 동가(bottom) 패산: 스택 12→0, 각 스택에서 아래층→위층
        for stack in range(12, -1, -1):
            for layer in [0, 1]:
                index = self.get_wall_tile_global_index('bottom', stack, layer)
                wang_indices.append(index)
        
        return wang_indices
    
    def get_next_wall_tile_index_for_deal_with_start_position(self):
        """배패용 시계방향 패산 뽑기 인덱스 계산 (시작 위치 반영) - WallManager 사용"""
        # WallManager에서 일반 패산에서 뽑힌 패 개수 가져오기
        drawn_count = len(self.wall_manager.dealt_regular_tiles)
        
        # 전체 패 개수 (4면 × 13스택 × 2층 = 104장)
        if drawn_count >= 104:
            return None
        
        # 시작 위치 정보 가져오기
        start_wall_position = self.wall_manager.start_wall_position
        start_stack_index = self.wall_manager.start_stack_index
        start_layer = self.wall_manager.start_layer
        
        # 패산 위치 매핑
        wall_positions = ['bottom', 'left', 'top', 'right']
        start_wall_idx = wall_positions.index(start_wall_position)
        
        # 현재 뽑을 패의 위치 계산
        tile_in_stack = drawn_count % 2  # 0=위층, 1=아래층
        stack_position = drawn_count // 2  # 몇 번째 스택인지
        
        # 시작 위치부터의 상대적 위치 계산
        current_wall_idx = start_wall_idx
        current_stack = start_stack_index
        remaining_stacks = stack_position
        
        # 시작 면에서 남은 스택 수 계산
        stacks_in_start_wall = 13 - start_stack_index
        
        if remaining_stacks < stacks_in_start_wall:
            # 시작 면 내에서 해결
            actual_stack = start_stack_index + remaining_stacks
            wall_pos = wall_positions[current_wall_idx]
        else:
            # 다른 면으로 넘어감
            remaining_stacks -= stacks_in_start_wall
            current_wall_idx = (current_wall_idx + 1) % 4
            
            # 완전한 면들을 건너뛰기
            while remaining_stacks >= 13:
                remaining_stacks -= 13
                current_wall_idx = (current_wall_idx + 1) % 4
            
            # 최종 위치
            actual_stack = remaining_stacks
            wall_pos = wall_positions[current_wall_idx]
        
        # 각 면에서 뽑는 방향 설정
        if wall_pos == 'bottom':  # 동가 - 오른쪽에서 왼쪽으로
            final_stack = 12 - actual_stack
        elif wall_pos == 'left':  # 남가 - 위에서 아래로
            final_stack = 12 - actual_stack
        elif wall_pos == 'top':  # 서가 - 왼쪽에서 오른쪽으로
            final_stack = actual_stack
        else:  # right (북가) - 아래에서 위로
            final_stack = actual_stack
        
        # 층 설정 (시작 층 고려)
        if drawn_count == 0:
            layer = start_layer
        else:
            layer = 1 - tile_in_stack
        
        # 글로벌 인덱스 계산
        tile_index = self.get_wall_tile_global_index(wall_pos, final_stack, layer)
        
        print(f"[DEBUG] 배패 패 뽑기 위치: wall={wall_pos}, stack={final_stack}, layer={layer}, index={tile_index}")
        return tile_index

    def get_next_wall_tile_index_for_deal(self):
        """배패용 시계방향 패산 뽑기 인덱스 계산 - WallManager 사용"""
        # WallManager에서 일반 패산에서 뽑힌 패 개수 가져오기  
        drawn_count = len(self.wall_manager.dealt_regular_tiles)
        
        # 패산 구조: 4면 × 13스택 × 2층 = 104장
        # 동가 패산부터 시계방향으로 뽑기
        # 각 스택에서 위층(layer=1) → 아래층(layer=0) 순서
        
        # 현재 뽑을 패의 위치 계산
        tile_in_stack = drawn_count % 2  # 0=위층, 1=아래층
        stack_position = drawn_count // 2  # 몇 번째 스택인지
        
        # 전체 스택 개수 (4면 × 13스택 = 52스택)
        if stack_position >= 52:
            return None
            
        # 어느 면의 몇 번째 스택인지 계산
        wall_index = stack_position // 13
        stack_in_wall = stack_position % 13
        
        # 각 면에서 뽑는 방향과 위치 설정 (테이블 중앙에서 바라보는 시계방향)
        if wall_index == 0:  # bottom (동가) - 오른쪽에서 왼쪽으로
            wall_pos = 'bottom'
            actual_stack = 12 - stack_in_wall
        elif wall_index == 1:  # left (남가) - 위에서 아래로
            wall_pos = 'left'
            actual_stack = 12 - stack_in_wall
        elif wall_index == 2:  # top (서가) - 왼쪽에서 오른쪽으로
            wall_pos = 'top'
            actual_stack = stack_in_wall
        else:  # right (북가) - 아래에서 위로
            wall_pos = 'right'
            actual_stack = stack_in_wall
        
        # 층 설정 (0=위층, 1=아래층)
        layer = 1 - tile_in_stack
        
        # 글로벌 인덱스 계산
        tile_index = self.get_wall_tile_global_index(wall_pos, actual_stack, layer)
        
        print(f"[DEBUG] 배패 패 뽑기 위치: wall={wall_pos}, stack={actual_stack}, layer={layer}, index={tile_index}")
        return tile_index

    def run(self):
        """게임 실행"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        if (self.phase == 'dice' or self.phase == 'wall_dice') and hasattr(self, 'waiting_for_user_input') and self.waiting_for_user_input:
                            # 주사위 단계에서 스페이스바로 다음 단계 진행
                            self.handle_dice_input()
                        elif self.game_phase == "finished":
                            # 게임 종료 후 스페이스로 다음 게임 시작
                            if self.current_game <= self.total_games:
                                self.start_next_game()
                            else:
                                print("🏁 모든 게임이 완료되었습니다!")
                        elif self.game_phase == "playing" and self.current_turn != 0:
                            # 스페이스바로 AI 턴 강제 시작 (디버그용)
                            print(f"🔧 [디버그] 스페이스바로 AI 턴 강제 시작: {self.player_names[self.current_turn]}")
                            self.ai_turn(self.current_turn)
                    elif event.key == pygame.K_r:
                        # R키로 게임 상태 복구 (디버그용)
                        if self.game_phase == "playing":
                            print(f"🔧 [디버그] R키로 게임 상태 복구 시도")
                            self.debug_fix_game_state()
                    elif event.key == pygame.K_d:
                        # D키로 상세 디버그 정보 출력
                        if self.game_phase == "playing":
                            print(f"🔧 [디버그] D키로 상세 상태 출력")
                            self.debug_print_detailed_state()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if (self.phase == 'dice' or self.phase == 'wall_dice') and hasattr(self, 'waiting_for_user_input') and self.waiting_for_user_input:
                        # 주사위 단계에서 마우스 클릭으로 다음 단계 진행
                        self.handle_dice_input()
                    else:
                        self.handle_click(event.pos)
            
            # 게임 상태 업데이트
            self.update()
            
            # 화면 렌더링
            self.render()
            pygame.display.flip()
            
            # 프레임 레이트 제한
            self.clock.tick(60)
        
        pygame.quit()

    def can_peng(self, player_idx, tile):
        """펑 가능 여부 체크 - 같은 패 2장 이상 보유"""
        if not tile:
            return False
        from mahjong_game import get_tile_base_name
        tile_base = get_tile_base_name(tile)
        count = sum(1 for t in self.hands[player_idx] if get_tile_base_name(t) == tile_base)
        return count >= 2
    
    def can_ming_gang(self, player_idx, tile):
        """명깡 가능 여부 체크 - 같은 패 3장 이상 보유"""
        if not tile:
            return False
        from mahjong_game import get_tile_base_name
        tile_base = get_tile_base_name(tile)
        count = sum(1 for t in self.hands[player_idx] if get_tile_base_name(t) == tile_base)
        return count >= 3
    
    def can_an_gang(self, player_idx):
        """암깡 가능 여부 체크 - 같은 패 4장 보유"""
        from mahjong_game import get_tile_base_name
        tile_counts = {}
        for tile in self.hands[player_idx]:
            tile_base = get_tile_base_name(tile)
            tile_counts[tile_base] = tile_counts.get(tile_base, 0) + 1
        
        # 4장 이상인 패들 반환
        return [tile_base for tile_base, count in tile_counts.items() if count >= 4]
    
    def can_jia_gang(self, player_idx, tile):
        """가깡 가능 여부 체크"""
        if not tile:
            return []
        
        from mahjong_game import get_tile_base_name, extract_meld_tile_base
        tile_base = get_tile_base_name(tile)
        available_jia_gang = []
        
        for meld in self.melds[player_idx]:
            if meld['type'] == 'peng':
                meld_tile_base = extract_meld_tile_base(meld)
                if meld_tile_base == tile_base:
                    available_jia_gang.append(tile)
        
        return available_jia_gang
    
    def get_available_actions(self, player_idx, discarded_tile, is_self_turn=False):
        """플레이어가 사용할 수 있는 액션 목록 반환"""
        actions = []
        
        # 엎어 상태 체크 (플레이어만)
        is_riichi = (player_idx == self.player_index and self.player_riichi)
        
        if is_self_turn:
            # 자기 턴에서 가능한 액션들 (암깡, 가깡만 - 리치는 패를 버린 후 별도 처리)
            if self.drawn_tile:
                # 암깡 체크 (엎어 상태에서도 가능)
                available_an_gang = self.can_an_gang(player_idx)
                if available_an_gang:
                    actions.append({'type': 'an_gang', 'tiles': available_an_gang})
                
                # 가깡 체크 (엎어 상태에서도 가능)
                available_jia_gang = self.can_jia_gang(player_idx, self.drawn_tile)
                if available_jia_gang:
                    actions.append({'type': 'jia_gang', 'tiles': available_jia_gang})
        else:
            # 다른 플레이어가 버린 패에 대한 액션들
            if discarded_tile:
                # 론 체크 (엎어 상태에서도 가능)
                if self.can_ron_with_tile(player_idx, discarded_tile):
                    actions.append({'type': 'ron', 'tile': discarded_tile})
                
                # 엎어 상태에서는 펑/명깡 불가 (멘젠을 깨는 액션)
                if not is_riichi:
                    # 펑 체크
                    if self.can_peng(player_idx, discarded_tile):
                        actions.append({'type': 'peng', 'tile': discarded_tile})
                    
                    # 명깡 체크
                    if self.can_ming_gang(player_idx, discarded_tile):
                        actions.append({'type': 'ming_gang', 'tile': discarded_tile})
                else:
                    print(f"🚫 {self.player_names[player_idx]}은 엎어 상태이므로 펑/명깡 불가")
        
        return actions
    
    def execute_peng(self, player_idx, tile):
        """펑 실행"""
        print(f"🎯 {self.player_names[player_idx]}이 {tile}로 펑!")
        
        # 하이라이트 해제
        self.clear_tile_highlight()
        
        # 버린 패를 버림패 더미에서 제거
        if self.last_discard_player is not None:
            discard_pile = self.discard_piles[self.last_discard_player]
            if discard_pile and discard_pile[-1] == tile:
                discard_pile.pop()
                print(f"✅ {tile}을 버림패에서 제거")
        
        # 플레이어 손패에서 같은 패 2장 제거 (펑 전 패 수 확인)
        hand = self.hands[player_idx]
        hand_size_before = len(hand)
        meld_count_before = len(self.melds[player_idx])
        
        print(f"🔧 펑 실행 전: 손패={hand_size_before}장, 멜드={meld_count_before}개")
        
        from mahjong_game import get_tile_base_name
        tile_base = get_tile_base_name(tile)
        removed_count = 0
        removed_tiles = []
        
        for i in range(len(hand) - 1, -1, -1):
            if removed_count >= 2:
                break
            hand_tile_base = get_tile_base_name(hand[i])
            if hand_tile_base == tile_base:
                removed_tile = hand.pop(i)
                removed_tiles.append(removed_tile)
                removed_count += 1
                print(f"✅ 손패에서 {removed_tile} 제거")
        
        print(f"🔧 펑 실행 중: {removed_count}장 제거 완료 - {removed_tiles}")
        
        # 제거 후 패 수 확인
        hand_size_after_remove = len(self.hands[player_idx])
        print(f"🔧 펑 패 제거 후: 손패={hand_size_after_remove}장 (이전: {hand_size_before}장, 제거: {removed_count}장)")
        
        # 멜드에 펑 추가
        peng_meld = {
            'type': 'peng',
            'tiles': [tile, tile, tile],  # 같은 패 3장
            'from_player': self.last_discard_player
        }
        self.melds[player_idx].append(peng_meld)
        print(f"✅ 펑 멜드 추가: {peng_meld}")
        
        # 펑한 플레이어가 다음 턴
        self.current_turn = player_idx
        print(f"🔄 펑 후 턴: {self.player_names[player_idx]}")
        
        # 펑 후 플래그 설정
        self.after_peng = True
        
        # 상태 초기화
        self.pending_action = None
        self.pending_tile = None
        self.last_discard_player = None
        
        # 펑 후에는 뽑은 패 정보 완전 초기화 (패를 뽑지 않고 바로 버려야 함)
        old_drawn_tile = self.drawn_tile
        self.drawn_tile = None
        self.player_waiting = False
        
        # 모든 플레이어의 drawn_tile 관련 상태 초기화 (AI 포함)
        if hasattr(self, 'ai_drawn_tiles'):
            self.ai_drawn_tiles = {}
        
        if old_drawn_tile:
            print(f"🔧 펑 후 뽑은 패 정보 완전 초기화: {old_drawn_tile} → None")
        
        # 손패 정렬
        player_position = self.get_player_screen_position(player_idx)
        self.hands[player_idx] = sort_hand_by_position(self.hands[player_idx], player_position)
        
        # 펑 후 패 수 디버깅 및 검증
        final_hand_size = len(self.hands[player_idx])
        final_meld_count = len(self.melds[player_idx])
        drawn_tile_info = f"drawn_tile={self.drawn_tile}" if player_idx == self.player_index else "AI"
        expected_hand_size = 14 - (final_meld_count * 3)  # 펑 후 패를 버려야 하는 상태
        
        print(f"🔧 펑 후 패 수: 손패={final_hand_size}장, 멜드={final_meld_count}개, {drawn_tile_info}")
        print(f"🔧 펑 후 예상 패 수: {expected_hand_size}장 (14 - {final_meld_count} * 3)")
        
        # 패 수가 맞지 않으면 경고
        if final_hand_size != expected_hand_size:
            print(f"🚨 펑 후 패 수 오류! 실제={final_hand_size}장, 예상={expected_hand_size}장")
            # 패 수 강제 조정 (임시 방편)
            if final_hand_size > expected_hand_size:
                excess = final_hand_size - expected_hand_size
                print(f"🔧 초과 패 {excess}장 제거 시도")
                for _ in range(excess):
                    if self.hands[player_idx]:
                        removed = self.hands[player_idx].pop()
                        print(f"🔧 초과 패 제거: {removed}")
                    else:
                        break
        
        # 펑 후에는 패를 버려야 함 (한국 마작 규칙 - 패를 뽑지 않음)
        if player_idx == self.player_index:
            # 플레이어인 경우
            self.waiting_for_player = True
            self.waiting_for_animation = False  # 애니메이션 대기 해제
            print("👤 펑 완료! 패를 선택해서 버리세요")
        else:
            # AI인 경우 - 패를 버리고 다음 플레이어로 순서 넘기기
            print(f"🤖 {self.player_names[player_idx]} 펑 완료, AI가 패 버리기")
            # AI가 패를 버린 후 다음 플레이어로 순서 넘기기 (다른 플레이어 액션 체크 없이)
            self.ai_discard_after_peng()

    def execute_gang(self, player_idx, gang_type, tile):
        """깡 실행"""
        if not tile and gang_type not in ['an_gang']:
            print(f"❌ execute_gang: tile이 None입니다! gang_type={gang_type}")
            return
        
        from mahjong_game import get_tile_base_name
        tile_base = get_tile_base_name(tile) if tile else gang_type
        meld = None  # meld 변수 초기화
        
        if gang_type == 'ming_gang':
            # 명깡: 손패에서 3장 제거
            removed_count = 0
            new_hand = []
            for t in self.hands[player_idx]:
                if get_tile_base_name(t) == tile_base and removed_count < 3:
                    removed_count += 1
                else:
                    new_hand.append(t)
            
            self.hands[player_idx] = new_hand
            
            meld = {
                'type': 'ming_gang',
                'tile': tile,
                'tiles': [tile] * 4,
                'from_player': self.last_discard_player
            }
            
        elif gang_type == 'an_gang':
            # 암깡: 손패에서 4장 제거
            removed_count = 0
            new_hand = []
            for t in self.hands[player_idx]:
                if get_tile_base_name(t) == tile_base and removed_count < 4:
                    removed_count += 1
                else:
                    new_hand.append(t)
            
            self.hands[player_idx] = new_hand
            
            meld = {
                'type': 'an_gang',
                'tile': tile_base,
                'tiles': [tile_base + '_1.png'] * 4,  # 실제 파일명으로 저장
                'from_player': None
            }
            
        elif gang_type == 'jia_gang':
            # 가깡: 손패에서 1장 제거하고 기존 펑을 깡으로 변경
            new_hand = []
            removed = False
            for t in self.hands[player_idx]:
                if get_tile_base_name(t) == tile_base and not removed:
                    removed = True
                else:
                    new_hand.append(t)
            
            self.hands[player_idx] = new_hand
            
            # 기존 펑 찾아서 깡으로 변경
            from mahjong_game import extract_meld_tile_base
            for existing_meld in self.melds[player_idx]:
                if existing_meld['type'] == 'peng':
                    meld_tile_base = extract_meld_tile_base(existing_meld)
                    if not meld_tile_base:
                        print(f"❌ 멜드 구조 오류: {existing_meld}")
                        continue
                    
                    if meld_tile_base == tile_base:
                        existing_meld['type'] = 'jia_gang'
                        # tile 키가 있으면 유지, 없으면 추가
                        if 'tile' not in existing_meld and 'tiles' in existing_meld:
                            existing_meld['tile'] = existing_meld['tiles'][0]
                        existing_meld['tiles'] = [existing_meld['tile']] * 4
                        break
            
            meld = None  # 이미 기존 멜드를 수정했으므로
        
        if meld:
            self.melds[player_idx].append(meld)
        
        print(f"🀄 {self.player_names[player_idx]}이 {tile_base} {gang_type}!")
        
        # 깡 후에는 왕패에서 보충패 뽑기
        replacement_tile = self.draw_flower_replacement_tile()
        if replacement_tile:
            print(f"🎴 깡 보충패: {replacement_tile}")
            
            # 보충패를 drawn_tile로 설정 (플레이어가 버릴 수 있도록)
            if player_idx == self.player_index:
                self.drawn_tile = replacement_tile
                print(f"🔧 플레이어 깡 보충패를 drawn_tile로 설정: {replacement_tile}")
                # 플레이어는 drawn_tile로 따로 관리하므로 손패에는 추가하지 않음
            else:
                # AI는 바로 손패에 추가
                self.hands[player_idx].append(replacement_tile)
                print(f"🔧 AI 깡 보충패를 손패에 추가: {replacement_tile}")
        
        # 깡한 플레이어가 다음 턴 (보충패를 뽑았으므로)
        self.current_turn = player_idx
        print(f"🔄 깡 후 턴: {self.player_names[player_idx]} (인덱스: {player_idx})")
        
        # 깡 후 플래그 설정 (펑과 동일하게 처리)
        self.after_peng = True
        
        # 상태 초기화
        self.pending_action = None
        self.pending_tile = None
        self.last_discard_player = None
        self.waiting_for_animation = False  # 애니메이션 대기 해제
        self.clear_tile_highlight()  # 하이라이트 해제
        
        print(f"🔧 깡 후 상태 설정 중...")
        print(f"   - current_turn: {self.current_turn}")
        print(f"   - player_index: {self.player_index}")
        print(f"   - 플레이어 턴인가: {player_idx == self.player_index}")
        print(f"   - drawn_tile: {self.drawn_tile}")
        
        # 깡 후에는 패를 버려야 함
        if player_idx == self.player_index:
            # 플레이어인 경우
            self.waiting_for_player = True
            print(f"👤 깡 완료! 패를 선택해서 버리세요 (waiting_for_player: {self.waiting_for_player})")
        else:
            # AI인 경우
            self.waiting_for_player = False  # AI 턴에서는 False로 설정
            print(f"🤖 {self.player_names[player_idx]} 깡 완료, AI가 패 버리기 (waiting_for_player: {self.waiting_for_player})")
            self.ai_discard_after_peng()  # 깡 후에도 펑과 동일하게 처리
        
        # 깡 후 패 수 디버깅 및 검증
        final_hand_size = len(self.hands[player_idx])
        final_meld_count = len(self.melds[player_idx])
        drawn_tile_info = f"drawn_tile={self.drawn_tile}" if player_idx == self.player_index else f"AI_hand={final_hand_size}"
        expected_hand_size = 14 - (final_meld_count * 3)  # 깡 후 패를 버려야 하는 상태
        
        print(f"🔧 깡 후 패 수: 손패={final_hand_size}장, 멜드={final_meld_count}개, {drawn_tile_info}")
        print(f"🔧 깡 후 예상 패 수: {expected_hand_size}장 (14 - {final_meld_count} * 3)")
        
        # 패 수가 맞지 않으면 경고
        if final_hand_size != expected_hand_size:
            print(f"🚨 깡 후 패 수 오류! 실제={final_hand_size}장, 예상={expected_hand_size}장")
            # 패 수 강제 조정 (임시 방편)
            if final_hand_size > expected_hand_size:
                excess = final_hand_size - expected_hand_size
                print(f"🔧 초과 패 {excess}장 제거 시도")
                for _ in range(excess):
                    if self.hands[player_idx]:
                        removed = self.hands[player_idx].pop()
                        print(f"🔧 초과 패 제거: {removed}")
                    else:
                        break
        
        print(f"🔧 깡 후 상태 설정 완료!")
        print(f"   - current_turn: {self.current_turn}")
        print(f"   - waiting_for_player: {self.waiting_for_player}")
        print(f"   - waiting_for_animation: {self.waiting_for_animation}")
        print(f"   - drawn_tile: {self.drawn_tile}")
    
    def execute_riichi(self, player_idx):
        """리치 실행 - 패를 버린 후에 호출됨"""
        print(f"🎯 {self.player_names[player_idx]}이 리치를 선언!")
        
        # 리치 상태로 설정
        self.player_riichi = True
        
        # 이미 패를 버린 상태이므로 뽑은 패 처리는 불필요
        self.drawn_tile = None
        self.player_waiting = False
        
        print(f"✅ 리치 완료! {self.player_names[player_idx]}이 리치 상태가 되었습니다.")
        
        # 리치 후 간방 상태 다이얼로그 표시
        if player_idx == self.player_index:
            self.check_and_show_tenpai_dialog(player_idx)
        
        # 리치 후에는 다른 플레이어 액션 체크 없이 다음 턴으로 진행
        print("🎯 리치 후 다음 턴 진행")
        self.advance_turn()

    def check_actions_after_discard(self, discard_player, discarded_tile):
        """패를 버린 후 다른 플레이어들의 액션 가능 여부 체크"""
        self.last_discard_player = discard_player
        available_actions = []
        
        # 다른 플레이어들 체크 (버린 플레이어 제외)
        for player_idx in range(4):
            if player_idx == discard_player:
                continue
            
            # 론 체크 (최우선)
            if self.can_ron_with_tile(player_idx, discarded_tile):
                print(f"🎉 {self.player_names[player_idx]}이 {discarded_tile}로 론!")
                self.game_winner = player_idx
                self.finish_game("ron", player_idx)
                return
                
            # 펑/깡 체크
            actions = self.get_available_actions(player_idx, discarded_tile, is_self_turn=False)
            for action in actions:
                action['player'] = player_idx
                available_actions.append(action)
        
        if available_actions:
            # 플레이어가 포함된 액션이 있으면 플레이어에게 먼저 물어보기
            player_actions = [action for action in available_actions if action['player'] == self.player_index]
            if player_actions:
                self.show_action_choice_ui(player_actions, discarded_tile)
            else:
                # AI만 가능한 액션들 처리
                self.process_ai_actions(available_actions, discarded_tile)
        else:
            # 아무도 액션할 수 없으면 다음 턴 진행
            self.continue_after_discard()
    
    def show_action_choice_ui(self, actions, discarded_tile):
        """플레이어에게 액션 선택 UI 표시"""
        self.pending_action = 'choice'
        self.pending_tile = discarded_tile
        self.action_choices = actions
        self.waiting_for_player = True
        
        # 버린 패 하이라이트 설정
        if discarded_tile:
            discard_positions = self.get_discarded_tile_positions(discarded_tile)
            self.set_tile_highlight(discarded_tile, discard_positions)
        
        if discarded_tile:
            print(f"🤔 {discarded_tile}에 대한 액션을 선택하세요:")
        else:
            print(f"🤔 가능한 액션을 선택하세요:")
        for i, action in enumerate(actions):
            action_name = {'peng': '펑', 'ming_gang': '명깡', 'an_gang': '암깡', 'jia_gang': '가깡'}.get(action['type'], action['type'])
            print(f"  {i+1}. {action_name}")
        print(f"  0. 패스")
    
    def get_discarded_tile_positions(self, tile):
        """버린 패의 화면 위치들 반환 - DiscardManager 사용"""
        return self.discard_manager.get_discarded_tile_positions(tile, self.discard_piles, self.screen_to_player)
    
    def calculate_discard_tile_position(self, screen_pos, tile_index):
        """버림패 더미에서 특정 패의 위치 계산 - DiscardManager 사용"""
        return self.discard_manager.calculate_discard_tile_position(screen_pos, tile_index)
    
    def set_tile_highlight(self, tile, positions):
        """펑/깡 시 패 하이라이트 설정 - DiscardManager 사용"""
        self.discard_manager.set_tile_highlight(tile, self.discard_piles, self.screen_to_player)
        print(f"✨ 패 하이라이트: {tile}")
    
    def clear_tile_highlight(self):
        """패 하이라이트 해제 - DiscardManager 사용"""
        self.discard_manager.clear_tile_highlight()
        print("🔄 패 하이라이트 해제")

    def process_ai_actions(self, actions, discarded_tile):
        """AI 액션들 처리 (우선순위: 깡 > 펑)"""
        # 깡이 있으면 깡 우선
        gang_actions = [action for action in actions if 'gang' in action['type']]
        if gang_actions:
            action = gang_actions[0]  # 첫 번째 깡 액션 선택
            self.execute_action(action, discarded_tile)
            return
        
        # 펑이 있으면 펑 실행
        peng_actions = [action for action in actions if action['type'] == 'peng']
        if peng_actions:
            action = peng_actions[0]  # 첫 번째 펑 액션 선택
            self.execute_action(action, discarded_tile)
            return
        
        # 아무 액션도 없으면 다음 턴
        self.continue_after_discard()
    
    def execute_action(self, action, discarded_tile):
        """액션 실행"""
        print(f"🎯 액션 실행: {action}, 패: {discarded_tile}")
        
        # action이 딕셔너리인 경우 처리
        if isinstance(action, dict):
            action_type = action['type']
            action_player = action.get('player', self.player_index)
            action_tile = action.get('tile', discarded_tile)
        else:
            # 문자열인 경우 (기존 호환성)
            action_type = action
            action_player = self.player_index
            action_tile = discarded_tile
        
        if action_type == "peng":
            self.execute_peng(action_player, action_tile or self.pending_tile)
        elif action_type == "ming_gang":
            self.execute_gang(action_player, "ming_gang", action_tile or self.pending_tile)
        elif action_type == "an_gang":
            # 암깡은 플레이어가 직접 선택해야 함
            available_an_gang = self.can_an_gang(action_player)
            if available_an_gang:
                # 첫 번째 가능한 암깡 실행 (실제로는 UI에서 선택해야 함)
                self.execute_gang(action_player, "an_gang", available_an_gang[0])
        elif action_type == "jia_gang":
            # 가깡: action에서 tiles 정보 사용
            if 'tiles' in action and action['tiles']:
                tile_to_gang = action['tiles'][0]
                print(f"🎯 가깡 실행: {tile_to_gang}")
                self.execute_gang(action_player, "jia_gang", tile_to_gang)
            else:
                print(f"❌ 가깡 타일 정보가 없음: {action}")
        elif action_type == "riichi":
            # 엎어 실행 (이미 패를 버린 후이므로 바로 다음 턴으로)
            self.execute_riichi(action_player)
            # 리치는 execute_riichi에서 advance_turn을 호출하므로 여기서는 추가 처리 안함
            return
        elif action_type == "pass":
            print("👤 패스 선택")
            self.continue_after_discard()
        
        # 액션 UI 숨기기
        self.action_choices = []
        self.pending_action = None
        self.pending_tile = None
        self.pending_player = None
        
        # 액션 실행 후 다음 턴으로 진행 (패스와 리치가 아닌 경우)
        if action_type not in ["pass", "riichi"]:
            self.continue_after_discard()
    
    def continue_after_discard(self):
        """패 버리기 후 정상적인 다음 턴 진행"""
        print(f"👤 턴 완료, 다음 턴 진행")
        
        # 애니메이션 대기 중이면 애니메이션 완료 후 진행하도록 설정
        if self.waiting_for_animation:
            print("🎬 애니메이션 대기 중, 완료 후 다음 턴 진행")
            self.animation_callback = self.advance_turn
            return
        
        # 즉시 다음 턴 진행
        self.advance_turn()
    
    def handle_action_choice(self, choice_index):
        """플레이어의 액션 선택 처리"""
        if not self.action_choices or choice_index < 0:
            return
        
        if choice_index == 0:
            # 패스
            print("👤 패스")
            
            # 자신의 턴인지 다른 플레이어 패에 대한 액션인지 구분
            is_self_turn_action = (self.pending_tile is None)
            
            # 엎어 액션인지 미리 체크 (action_choices 초기화 전에)
            is_riichi_action = any(action.get('type') == 'riichi' for action in self.action_choices)
            
            self.pending_action = None
            self.pending_tile = None
            self.action_choices = []
            
            if is_self_turn_action:
                # 자신의 턴에서 패스한 경우
                if is_riichi_action:
                    # 엎어 패스 - 이미 패를 버린 상태이므로 다른 플레이어 액션 체크
                    print("👤 엎어 패스 - 다른 플레이어 액션 체크")
                    # 마지막으로 버린 패로 다른 플레이어 액션 체크
                    if self.discard_piles[self.player_index]:
                        last_discarded = self.discard_piles[self.player_index][-1]
                        self.check_actions_after_discard(self.player_index, last_discarded)
                    else:
                        self.advance_turn()
                else:
                    # 일반 액션 패스 - 패 버리기 대기
                    self.waiting_for_player = True
                    print("👤 패를 선택해서 버리세요")
            else:
                # 다른 플레이어가 버린 패에 대한 패스 - 다음 턴 진행
                self.waiting_for_player = False
                self.continue_after_discard()
        elif choice_index <= len(self.action_choices):
            # 액션 선택
            action = self.action_choices[choice_index - 1]
            print(f"👤 {action['type']} 선택")
            temp_tile = self.pending_tile  # 먼저 저장
            self.pending_action = None
            self.pending_tile = None
            self.action_choices = []
            self.waiting_for_player = False
            self.execute_action(action, temp_tile)

    def render_action_choice_ui(self):
        """액션 선택 UI 렌더링 - 화면 오른쪽 끝 가장 밑에"""
        if not self.action_choices:
            return
        
        # 다이얼로그 위치 (화면 오른쪽 끝 가장 밑)
        button_width = 80
        button_height = 35
        button_spacing = 5
        margin = 10
        
        # 전체 버튼들의 높이 계산 (세로로 배치)
        total_buttons = len(self.action_choices) + 1  # 액션들 + 패스
        total_height = total_buttons * button_height + (total_buttons - 1) * button_spacing
        
        # 오른쪽 끝에서 margin만큼 떨어진 위치
        start_x = SCREEN_WIDTH - button_width - margin
        start_y = SCREEN_HEIGHT - total_height - margin
        
        # 제목 텍스트 (버튼 위에)
        if self.pending_tile:
            # 패 이름에서 .png 제거하고 기본 이름만 표시
            from mahjong_game import get_tile_base_name
            tile_name = get_tile_base_name(self.pending_tile)
            title_text = f"{tile_name}"
        else:
            title_text = "액션 선택"
        
        title_surface = self.resources.render_text_with_emoji(title_text, "small", COLORS["highlight"])
        title_x = start_x + (button_width - title_surface.get_width()) // 2
        title_y = start_y - 20
        self.screen.blit(title_surface, (title_x, title_y))
        
        # 액션 버튼들 렌더링 (세로로 배치)
        for i, action in enumerate(self.action_choices):
            button_y = start_y + i * (button_height + button_spacing)
            button_rect = pygame.Rect(start_x, button_y, button_width, button_height)
            
            # 버튼 배경
            pygame.draw.rect(self.screen, (70, 130, 180), button_rect)  # 스틸 블루
            pygame.draw.rect(self.screen, (255, 255, 255), button_rect, 2)  # 흰색 테두리
            
            # 액션 이름 (한글로 명확하게)
            action_names = {
                'peng': '펑',
                'ming_gang': '명깡', 
                'an_gang': '암깡',
                'jia_gang': '가깡',
                'riichi': '엎어'
            }
            action_text = action_names.get(action['type'], action['type'])
            
            # 텍스트 렌더링
            text_surface = self.resources.render_text_with_emoji(action_text, "small", (255, 255, 255))
            text_x = start_x + (button_width - text_surface.get_width()) // 2
            text_y = button_y + (button_height - text_surface.get_height()) // 2
            self.screen.blit(text_surface, (text_x, text_y))
        
        # 패스 버튼
        pass_button_y = start_y + len(self.action_choices) * (button_height + button_spacing)
        pass_button_rect = pygame.Rect(start_x, pass_button_y, button_width, button_height)
        
        # 패스 버튼 배경 (다른 색상)
        pygame.draw.rect(self.screen, (128, 128, 128), pass_button_rect)  # 회색
        pygame.draw.rect(self.screen, (255, 255, 255), pass_button_rect, 2)  # 흰색 테두리
        
        # 패스 텍스트
        pass_text = "패스"
        pass_surface = self.resources.render_text_with_emoji(pass_text, "small", (255, 255, 255))
        pass_text_x = start_x + (button_width - pass_surface.get_width()) // 2
        pass_text_y = pass_button_y + (button_height - pass_surface.get_height()) // 2
        self.screen.blit(pass_surface, (pass_text_x, pass_text_y))

    def check_winning_hand_with_melds(self, player_idx, is_tsumo=False):
        """멜드를 포함한 화료 체크"""
        hand = self.hands[player_idx]
        melds = self.melds[player_idx]
        flower_count = len(self.flower_tiles[player_idx])
        
        # 멘젠 여부 확인 (멜드가 없으면 멘젠)
        is_menzen = len(melds) == 0
        
        # 멜드를 가상의 패로 변환하여 전체 패 구성 만들기
        virtual_hand = hand.copy()
        
        # 각 멜드를 손패에 추가 (화료 체크용) - 공통 함수 사용
        from mahjong_game import convert_melds_to_virtual_tiles
        virtual_hand.extend(convert_melds_to_virtual_tiles(melds))
        
        # 표준 화료 체크 실행 (멘젠 여부 전달)
        result = is_winning_hand(virtual_hand, is_tsumo=is_tsumo, is_menzen=is_menzen, flower_count=flower_count, debug=False)
        return result
    
    def check_winning_hand_with_melds_temp(self, player_idx, temp_hand, is_tsumo=False):
        """임시 손패로 멜드를 포함한 화료 체크"""
        melds = self.melds[player_idx]
        flower_count = len(self.flower_tiles[player_idx])
        
        # 멘젠 여부 확인 (멜드가 없으면 멘젠)
        is_menzen = len(melds) == 0
        
        # 멜드를 가상의 패로 변환하여 전체 패 구성 만들기
        virtual_hand = temp_hand.copy()
        
        # 각 멜드를 손패에 추가 (화료 체크용) - 공통 함수 사용
        from mahjong_game import convert_melds_to_virtual_tiles
        virtual_hand.extend(convert_melds_to_virtual_tiles(melds))
        
        # 표준 화료 체크 실행 (멘젠 여부 전달)
        result = is_winning_hand(virtual_hand, is_tsumo=is_tsumo, is_menzen=is_menzen, flower_count=flower_count, debug=False)
        return result

    def can_ron_with_tile(self, player_idx, discarded_tile):
        """론 가능 여부 체크 - 버린 패를 받아서 화료할 수 있는지"""
        hand = self.hands[player_idx]
        melds = self.melds[player_idx]
        flower_count = len(self.flower_tiles[player_idx])
        
        # 멘젠 여부 확인 (멜드가 없으면 멘젠)
        is_menzen = len(melds) == 0
        
        # 1. 멘젠 상태에서 7쌍 패턴 체크 (13장 + 론패 1장 = 14장)
        if is_menzen and len(hand) == 13:
            from mahjong_game import can_complete_seven_pairs_with_tile, is_winning_hand
            if can_complete_seven_pairs_with_tile(hand, discarded_tile):
                # 7쌍 패턴이지만 역 체크도 해야 함 (칠대작 역 필요)
                temp_hand = hand + [discarded_tile]
                if is_winning_hand(temp_hand, is_tsumo=False, is_menzen=is_menzen, flower_count=flower_count, debug=True):
                    print(f"🎯 7쌍 론 가능! {discarded_tile}로 7쌍 완성 (칠대작 역 포함)")
                    return True
                else:
                    print(f"🚫 7쌍 패턴이지만 역이 없어서 론 불가")
                    return False
        
        # 2. 기본 화료 패턴 체크 (4몸통+1머리)
        # 임시로 버린 패를 손패에 추가
        temp_hand = hand + [discarded_tile]
        
        # 론 체크 시점에서 손패 수 계산 (버린 패를 받은 상태)
        expected_hand_size = 14 - (len(melds) * 3)
        if len(temp_hand) != expected_hand_size:
            return False
        
        # 멜드를 가상의 패로 변환하여 전체 패 구성 만들기
        virtual_hand = temp_hand.copy()
        
        # 각 멜드를 손패에 추가 (화료 체크용) - 공통 함수 사용
        from mahjong_game import convert_melds_to_virtual_tiles
        virtual_hand.extend(convert_melds_to_virtual_tiles(melds))
        
        # 표준 화료 체크 실행 (멘젠 여부 전달)
        from mahjong_game import is_winning_hand
        result = is_winning_hand(virtual_hand, is_tsumo=False, is_menzen=is_menzen, flower_count=flower_count)
        return result

    def handle_action_choice_click(self, pos):
        """액션 선택 UI에서 마우스 클릭 처리"""
        # 클릭 소리 재생
        self.play_click_sound()
        
        if not self.action_choices:
            return False
        
        button_width = 80
        button_height = 35
        button_spacing = 5
        margin = 10
        
        total_buttons = len(self.action_choices) + 1
        total_height = total_buttons * button_height + (total_buttons - 1) * button_spacing
        
        start_x = SCREEN_WIDTH - button_width - margin
        start_y = SCREEN_HEIGHT - total_height - margin
        
        # 액션 버튼들 체크
        for i, action in enumerate(self.action_choices):
            button_y = start_y + i * (button_height + button_spacing)
            button_rect = pygame.Rect(start_x, button_y, button_width, button_height)
            
            if button_rect.collidepoint(pos):
                print(f"👤 액션 선택: {action['type']}")
                
                # 액션 선택 시 클릭 소리 재생
                self.play_click_sound()
                
                self.pending_action = None
                self.pending_tile = None
                self.action_choices = []
                self.waiting_for_player = False
                
                self.execute_action(action, self.pending_tile)
                return True
        
        # 패스 버튼 체크
        pass_button_y = start_y + len(self.action_choices) * (button_height + button_spacing)
        pass_button_rect = pygame.Rect(start_x, pass_button_y, button_width, button_height)
        
        if pass_button_rect.collidepoint(pos):
            print("👤 패스 클릭")
            
            # 패스 선택 시 클릭 소리 재생
            self.play_click_sound()
            
            # 하이라이트 해제
            self.clear_tile_highlight()
            
            is_self_turn_action = (self.pending_tile is None)
            
            # 엎어 액션인지 미리 체크 (action_choices 초기화 전에)
            is_riichi_action = any(action.get('type') == 'riichi' for action in self.action_choices)
            
            self.pending_action = None
            self.pending_tile = None
            self.action_choices = []
            
            if is_self_turn_action:
                if is_riichi_action:
                    # 엎어 패스 - 이미 패를 버린 상태이므로 다른 플레이어 액션 체크
                    print("👤 엎어 패스 - 다른 플레이어 액션 체크")
                    if self.discard_piles[self.player_index]:
                        last_discarded = self.discard_piles[self.player_index][-1]
                        self.check_actions_after_discard(self.player_index, last_discarded)
                    else:
                        self.advance_turn()
                else:
                    # 일반 액션 패스 - 패 버리기 대기
                    self.waiting_for_player = True
                    print("👤 패를 선택해서 버리세요")
            else:
                self.waiting_for_player = False
                self.continue_after_discard()
            return True
        
        return False

    def finish_game(self, result_type, winner_idx):
        """게임 종료 처리 및 점수 계산"""
        print(f"\n🏁 === 게임 종료 ({self.current_game}/{self.total_games}판) ===")
        
        # 화료인 경우 역 정보 다이얼로그 표시
        if result_type in ["tsumo", "ron"] and winner_idx is not None:
            self.show_winning_dialog(result_type, winner_idx)
            return  # 다이얼로그가 닫힐 때까지 대기
        
        # 실제 게임 종료 처리
        self.complete_game_finish(result_type, winner_idx)
    
    def show_winning_dialog(self, result_type, winner_idx):
        """화료 시 역 정보 다이얼로그 표시"""
        # 승자의 패 정보 수집
        hand = self.hands[winner_idx]
        melds = self.melds[winner_idx]
        flower_count = len(self.flower_tiles[winner_idx])
        
        # 역 정보 계산
        from mahjong_game import check_yaku, calculate_korean_mahjong_points
        
        # 론 시 가져온 패 정보 먼저 수집
        ron_tile_info = None
        ron_tile = None
        if result_type == "ron" and self.last_discard_player is not None:
            discard_pile = self.discard_piles[self.last_discard_player]
            if discard_pile:
                ron_tile = discard_pile[-1]  # 마지막으로 버린 패
                self.ron_tile = ron_tile  # 론한 패 저장 (하이라이트용)
                ron_tile_info = {
                    'tile': ron_tile,
                    'from_player': self.last_discard_player,
                    'from_player_name': self.player_names[self.last_discard_player]
                }
        
        # 멜드를 포함한 가상 손패 생성
        virtual_hand = hand.copy()
        
        # 론한 패를 손패에 추가 (14장 완성)
        if result_type == "ron" and ron_tile:
            virtual_hand.append(ron_tile)
            print(f"🎯 론한 패 {ron_tile}를 가상 손패에 추가하여 역 계산")
        
        # 각 멜드를 손패에 추가 (화료 체크용) - 공통 함수 사용
        from mahjong_game import convert_melds_to_virtual_tiles
        virtual_hand.extend(convert_melds_to_virtual_tiles(melds))
        
        # 멘젠 여부 확인 (멜드가 없으면 멘젠)
        is_menzen = len(melds) == 0
        
        # 역 체크
        is_tsumo = (result_type == "tsumo")
        player_wind = "동"  # 간단화
        round_wind = "동"
        
        print(f"🎯 역 계산: 가상손패={len(virtual_hand)}장, 멘젠={is_menzen}, 쯔모={is_tsumo}")
        yaku_list = check_yaku(virtual_hand, is_tsumo, is_menzen, player_wind, round_wind, flower_count)
        
        # 겐쇼 점수 계산 (쯔모한 패 개수)
        from mahjong_game import calculate_gensho_count
        gensho_count = calculate_gensho_count(hand, melds, is_tsumo)
        
        yaku_points = calculate_korean_mahjong_points(yaku_list, flower_count, is_tsumo, is_menzen, gensho_count)
        print(f"🎯 계산된 역: {yaku_list}, 겐쇼: {gensho_count}개, 점수: {yaku_points}")
        
        # 다이얼로그 정보 저장
        self.winning_dialog_active = True
        self.winning_yaku_info = {
            'yaku_list': yaku_list,
            'yaku_points': yaku_points,
            'hand': hand,
            'melds': melds,
            'flower_count': flower_count,
            'gensho_count': gensho_count,
            'ron_tile_info': ron_tile_info,
            'is_menzen': is_menzen,
            'show_ai_hand': winner_idx != self.player_index  # AI가 이겼을 때만 패 공개
        }
        self.winning_player_idx = winner_idx
        self.winning_result_type = result_type
        
        print(f"🎉 {self.player_names[winner_idx]} 화료!")
        print(f"역: {', '.join(yaku_list) if yaku_list else '없음'}")
        print(f"점수: {yaku_points}점")
    
    def complete_game_finish(self, result_type, winner_idx):
        """실제 게임 종료 처리 (다이얼로그 후)"""
        # 게임 결과 기록
        game_result = {
            'game_number': self.current_game,
            'result_type': result_type,
            'winner': winner_idx,
            'scores_before': self.player_scores.copy(),
            'scores_after': None
        }
        
        # 점수 계산 (한국 마작 기준 - 통합된 계산 함수 사용)
        if hasattr(self, 'winning_yaku_info') and self.winning_yaku_info:
            yaku_list = self.winning_yaku_info['yaku_list']
            flower_count = self.winning_yaku_info['flower_count']
            gensho_count = self.winning_yaku_info.get('gensho_count', 0)
            is_menzen = self.winning_yaku_info.get('is_menzen', True)
            
            # 통합된 점수 계산 함수 사용
            from mahjong_game import calculate_korean_mahjong_points
            is_tsumo = (result_type == "tsumo")
            base_points = calculate_korean_mahjong_points(yaku_list, flower_count, is_tsumo, is_menzen, gensho_count)
            
            # 엎어 보너스 추가
            riichi_bonus = 0
            if winner_idx == self.player_index and self.player_riichi:
                riichi_bonus = self.riichi_bonus
                print(f"🎯 엎어 보너스: +{riichi_bonus}점")
            
            # 총 점수 계산
            points = base_points + riichi_bonus
        else:
            points = 10  # 기본 점수
        
        if result_type == "tsumo":
            # 다른 3명이 각각 점수를 지불
            points_per_player = points
            for i in range(4):
                if i != winner_idx:
                    self.player_scores[i] -= points_per_player
                    self.player_scores[winner_idx] += points_per_player
            print(f"🎉 {self.player_names[winner_idx]} 쯔모! +{points_per_player * 3}점")
            
        elif result_type == "ron":
            # 론: 버린 사람만 지불
            loser_idx = self.last_discard_player
            if loser_idx is not None:
                self.player_scores[loser_idx] -= points
                self.player_scores[winner_idx] += points
                print(f"🎉 {self.player_names[winner_idx]} 론! +{points}점")
                print(f"😢 {self.player_names[loser_idx]} -{points}점")
            
        elif result_type == "draw":
            print("🤝 유국 - 점수 변화 없음")
        
        # 점수 결과 기록
        game_result['scores_after'] = self.player_scores.copy()
        self.game_results.append(game_result)
        
        # 현재 점수 출력
        print("\n📊 현재 점수:")
        for i, score in enumerate(self.player_scores):
            print(f"  {self.player_names[i]}: {score}점")
        
        # 게임 상태를 finished로 변경
        self.phase = 'finished'
        self.game_phase = "finished"
        
        print(f"🎮 {self.current_game}/{self.total_games}판 완료")
        
        # 다음 게임 동가 설정을 위해 승자 정보 저장
        if result_type in ["tsumo", "ron"] and winner_idx is not None:
            # 화료한 경우: 승자가 다음 게임 동가
            self.game_winner = winner_idx
            print(f"🎯 다음 게임 동가: {self.player_names[winner_idx]} (화료)")
        else:
            # 유국인 경우: 동가 유지
            self.game_winner = None
            print(f"🎯 다음 게임 동가: {self.player_names[self.east_player]} (유국으로 유지)")
        
        # 게임 번호 증가 (다음 게임 준비)
        self.current_game += 1
        
        if self.current_game <= self.total_games:
            print("⏳ 스페이스 키나 화면 클릭으로 다음 게임 시작")
        else:
            print("🏆 모든 게임 완료! 최종 결과:")
            self.show_final_results()

    def show_final_results(self):
        """최종 결과 표시"""
        print("\n🏆 === 최종 결과 ===")
        
        # 점수 순으로 정렬
        player_results = [(i, self.player_names[i], self.player_scores[i]) for i in range(4)]
        player_results.sort(key=lambda x: x[2], reverse=True)
        
        print("📊 최종 순위:")
        for rank, (idx, name, score) in enumerate(player_results, 1):
            if rank == 1:
                print(f"  🥇 1위: {name} - {score}점")
            elif rank == 2:
                print(f"  🥈 2위: {name} - {score}점")
            elif rank == 3:
                print(f"  🥉 3위: {name} - {score}점")
            else:
                print(f"  4위: {name} - {score}점")
        
        # 게임 통계
        wins_count = [0, 0, 0, 0]
        for result in self.game_results:
            if result['winner'] is not None:
                wins_count[result['winner']] += 1
        
        print("\n🎯 승리 횟수:")
        for i in range(4):
            print(f"  {self.player_names[i]}: {wins_count[i]}승")

    def render_game_finished_ui(self):
        """게임 종료 UI 렌더링"""
        # 반투명 배경
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # 메인 패널 (크기 증가)
        panel_width = 450  # 400 → 450으로 증가
        panel_height = 280  # 220 → 280으로 증가 (더 많은 공간)
        panel_x = (SCREEN_WIDTH - panel_width) // 2
        panel_y = (SCREEN_HEIGHT - panel_height) // 2
        
        # 패널 배경
        pygame.draw.rect(self.screen, (40, 40, 40), (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, (255, 255, 255), (panel_x, panel_y, panel_width, panel_height), 3)
        
        # 제목 (작게) - 올바른 판수 표시
        if self.current_game > self.total_games:
            title_text = "[최종] 결과"
        else:
            # current_game이 이미 증가된 상태이므로 -1 해서 실제 완료된 판수 표시
            completed_game = self.current_game - 1 if self.current_game > 1 else 1
            title_text = f"[{completed_game}판] 종료"
        
        title_surface = self.resources.render_text_with_emoji(title_text, "medium", COLORS["highlight"])
        title_x = panel_x + (panel_width - title_surface.get_width()) // 2
        title_y = panel_y + 15
        self.screen.blit(title_surface, (title_x, title_y))
        
        # 현재 점수 표시 (작게)
        score_y = title_y + 30
        score_title = self.resources.render_text_with_emoji("[점수] 현재 점수", "small", COLORS["text"])
        score_title_x = panel_x + (panel_width - score_title.get_width()) // 2
        self.screen.blit(score_title, (score_title_x, score_y))
        
        # 각 플레이어 점수 (작게)
        for i, score in enumerate(self.player_scores):
            player_text = f"{self.player_names[i]}: {score}점"
            color = COLORS["highlight"] if i == self.game_winner else COLORS["text"]
            player_surface = self.resources.render_text_with_emoji(player_text, "small", color)
            player_x = panel_x + (panel_width - player_surface.get_width()) // 2
            player_y = score_y + 25 + i * 25  # 20 + i * 18 → 25 + i * 25로 증가 (행간 증가)
            self.screen.blit(player_surface, (player_x, player_y))
        
        # 안내 메시지
        if self.current_game < self.total_games:
            guide_text = "[안내] 스페이스 키나 화면 클릭으로 다음 게임 시작"
            next_game_text = f"다음: {self.current_game + 1}/{self.total_games}판"
        else:
            guide_text = "[완료] 모든 게임 완료! ESC 키로 종료"
            
            # 최종 순위 표시 (작게)
            player_results = [(i, self.player_names[i], self.player_scores[i]) for i in range(4)]
            player_results.sort(key=lambda x: x[2], reverse=True)
            
            rank_y = player_y + 25
            rank_title = self.resources.render_text_with_emoji("[순위] 최종 순위", "small", COLORS["highlight"])
            rank_title_x = panel_x + (panel_width - rank_title.get_width()) // 2
            self.screen.blit(rank_title, (rank_title_x, rank_y))
            
            for rank, (idx, name, score) in enumerate(player_results[:3], 1):
                if rank == 1:
                    rank_text = f"[1위] {name} ({score}점)"
                elif rank == 2:
                    rank_text = f"[2위] {name} ({score}점)"
                else:
                    rank_text = f"[3위] {name} ({score}점)"
                
                rank_surface = self.resources.render_text_with_emoji(rank_text, "small", COLORS["text"])
                rank_x = panel_x + (panel_width - rank_surface.get_width()) // 2
                rank_y_pos = rank_y + 20 + (rank - 1) * 20  # 15 + (rank - 1) * 15 → 20 + (rank - 1) * 20로 증가 (순위 행간 증가)
                self.screen.blit(rank_surface, (rank_x, rank_y_pos))
            
            next_game_text = ""
        
        # 안내 메시지 표시 (작게) - 패널 높이 증가에 맞춰 조정
        guide_surface = self.resources.render_text_with_emoji(guide_text, "small", COLORS["highlight"])
        guide_x = panel_x + (panel_width - guide_surface.get_width()) // 2
        guide_y = panel_y + panel_height - 30  # 패널 높이 증가에 맞춰 조정
        self.screen.blit(guide_surface, (guide_x, guide_y))
        
        if next_game_text:
            next_surface = self.resources.render_text_with_emoji(next_game_text, "small", COLORS["text"])
            next_x = panel_x + (panel_width - next_surface.get_width()) // 2
            next_y = guide_y + 15  # 패널 높이 증가에 맞춰 간격 조정
            self.screen.blit(next_surface, (next_x, next_y))

    def start_next_game(self):
        """다음 게임 시작"""
        if self.current_game > self.total_games:
            print("🏁 모든 게임이 완료되었습니다!")
            return
        
        print(f"\n🎮 === {self.current_game}판 시작 ===")
        
        # 점수와 게임 기록 백업 (리셋되지 않도록)
        backup_scores = self.player_scores.copy()
        backup_game_results = self.game_results.copy()
        backup_current_game = self.current_game
        backup_total_games = self.total_games
        
        # 게임 상태 리셋 (점수와 게임 기록은 유지)
        self.game_phase = "dice_rolling"
        self.phase = 'dice'
        self.current_turn = 0
        self.turn_counter = 0
        self.waiting_for_player = False
        self.drawn_tile = None
        self.game_winner = None
        
        # 패 관련 초기화 - 공통 함수 사용
        from mahjong_game import init_player_game_data, init_game_flags
        
        player_data = init_player_game_data()
        self.hands = player_data['hands']
        self.discard_piles = player_data['discard_piles']
        self.flower_tiles = player_data['flower_tiles']
        self.melds = player_data['melds']
        
        # 패산 관리는 WallManager에 완전히 위임 - main.py에서는 추적하지 않음
        
        # 게임 플래그들 초기화 - 공통 함수 사용
        game_flags = init_game_flags()
        for key, value in game_flags.items():
            setattr(self, key, value)
        
        # 캐시 초기화
        self.winning_hints_cache = {}
        
        # 간방 상태 초기화
        self.player_tenpai_state = False
        self.tenpai_dialog_shown = False
        self.last_tenpai_tiles = []
        self.tenpai_options = []
        self.last_tenpai_options = []

        
        # 버림패 관리자 초기화
        if hasattr(self, 'discard_manager'):
            self.discard_manager.tile_positions = {}
            self.discard_manager.clear_tile_highlight()
        
        # 점수와 게임 기록 복원
        self.player_scores = backup_scores
        self.game_results = backup_game_results
        self.current_game = backup_current_game
        self.total_games = backup_total_games
        
        # 플레이어 이름 설정 (위치 정보 포함)
        self.player_names = ["플레이어", "김민수", "박지영", "이준호"]
        self.players = ["human", "ai", "ai", "ai"]
        
        # 화면 위치 매핑 (플레이어는 항상 하단)
        self.screen_to_player = {
            'bottom': 0,  # 플레이어
            'right': 1,   # AI1
            'top': 2,     # AI2
            'left': 3     # AI3
        }
        
        # 이전 게임 결과에 따라 동가 결정 (한국 마작 규칙)
        if hasattr(self, 'game_winner') and self.game_winner is not None:
            # 화료한 플레이어가 동가
            self.east_player = self.game_winner
            print(f"🏆 이전 게임 화료자 {self.player_names[self.game_winner]}이 동가가 됩니다.")
        else:
            # 무승부(유국)면 이전 동가 유지
            if hasattr(self, 'east_player') and self.east_player is not None:
                print(f"🤝 유국으로 이전 동가 {self.player_names[self.east_player]} 유지")
            else:
                # 예외 상황: 동가가 설정되지 않은 경우 기본값 설정
                self.east_player = 0
                print(f"🎲 동가: {self.player_names[self.east_player]} (기본값)")
        
        # 동가 결정 후 플레이어 이름 업데이트
        self.update_player_names_with_positions()
        
        # WallManager 완전히 리셋
        if hasattr(self, 'wall_manager'):
            del self.wall_manager
        self.wall_manager = None
        
        # 패산 구성
        self.wall_tiles = create_tiles()
        print(f"[DEBUG] create_tiles() -> {len(self.wall_tiles)}장")
        random.shuffle(self.wall_tiles)
        print(f"[DEBUG] self.wall_tiles after shuffle -> {len(self.wall_tiles)}장")
        
        # 새로운 WallManager 생성
        self.wall_manager = WallManager(self.wall_tiles, self.screen)
        
        # WallManager 상태 확인 (디버그)
        print(f"[DEBUG] 새 WallManager 생성 후:")
        debug_info = self.wall_manager.get_debug_info()
        print(f"  - dealt_tiles: {debug_info['dealt_tiles']}장")
        print(f"  - remaining_tiles: {debug_info['remaining_tiles']}장")
        
        # 패산 위치 결정 주사위 굴리기 (동가는 이미 결정됨)
        print(f"🎲 {self.current_game}판 동가: {self.player_names[self.east_player]}")
        self.phase = 'dice'
        self.dice_step = 'wall_only'
        self.waiting_for_user_input = True
        self.roll_dice_for_wall_position()
        
        print("=== 게임 시작 ===")
    
    def get_discard_pile_next_position(self, player_idx):
        """버림패 더미에서 다음 패가 놓일 정확한 위치 계산"""
        pos = self.get_player_screen_position(player_idx)
        pile = self.discard_piles[player_idx]
        next_index = len(pile)  # 현재 더미 크기가 다음 인덱스
        
        discard_areas = {
            "top": {"center_x": TABLE_CENTER_X, "center_y": TABLE_CENTER_Y - 188, "rotation": 180},
            "right": {"center_x": TABLE_CENTER_X + 120, "center_y": TABLE_CENTER_Y - 24, "rotation": 90},
            "bottom": {"center_x": TABLE_CENTER_X, "center_y": TABLE_CENTER_Y + 92, "rotation": 0},
            "left": {"center_x": TABLE_CENTER_X - 168, "center_y": TABLE_CENTER_Y - 24, "rotation": -90}
        }
        
        if pos not in discard_areas:
            return self.get_discard_pile_center(player_idx)
            
        area = discard_areas[pos]
        tile_size = (36, 48)
        tile_spacing = 38
        
        row = next_index // 6
        col = next_index % 6
        
        if area["rotation"] == 0:  # 하단 (플레이어)
            start_x = area["center_x"] - (6 * tile_spacing) // 2
            tile_x = start_x + col * tile_spacing
            tile_y = area["center_y"] + row * 48
        elif area["rotation"] == 180:  # 상단 (AI2)
            start_x = area["center_x"] - (6 * tile_spacing) // 2
            tile_x = start_x + (5 - col) * tile_spacing
            tile_y = area["center_y"] - row * 48
        elif area["rotation"] == 90:  # 우측 (AI1)
            start_y = area["center_y"] - (6 * tile_spacing) // 2
            tile_x = area["center_x"] + row * 48
            tile_y = start_y + (5 - col) * tile_spacing
        else:  # rotation == -90, 좌측 (AI3)
            start_y = area["center_y"] - (6 * tile_spacing) // 2
            tile_x = area["center_x"] - row * 48
            tile_y = start_y + col * tile_spacing
            
        return (tile_x, tile_y)

    def clear_winning_hints_cache(self):
        """화료 힌트 캐시 클리어"""
        if hasattr(self, 'winning_hints_cache'):
            self.winning_hints_cache.clear()
    
    def clear_click_buffer(self):
        """클릭 이벤트 버퍼 초기화"""
        self.click_buffer = []
        print("🧹 클릭 버퍼 초기화")
    
    def debug_fix_game_state(self):
        """게임 상태 복구 (디버그용)"""
        print(f"🔧 === 게임 상태 복구 시작 ===")
        print(f"현재 턴: {self.current_turn} ({self.player_names[self.current_turn]})")
        print(f"waiting_for_player: {self.waiting_for_player}")
        print(f"waiting_for_animation: {self.waiting_for_animation}")
        print(f"pending_action: {self.pending_action}")
        print(f"action_choices: {self.action_choices}")
        
        # 애니메이션 상태 초기화
        if self.waiting_for_animation:
            print("🔧 애니메이션 대기 상태 해제")
            self.waiting_for_animation = False
            self.animation_callback = None
            self.discard_animations = []
        
        # 액션 상태 초기화
        if self.pending_action or self.action_choices:
            print("🔧 액션 상태 초기화")
            self.pending_action = None
            self.pending_tile = None
            self.action_choices = []
            self.clear_tile_highlight()
        
        # 플레이어 턴인 경우 대기 상태로 설정
        if self.current_turn == self.player_index:
            print("🔧 플레이어 턴으로 복구")
            self.waiting_for_player = True
            
            # 손패 수 체크
            current_hand_size = len(self.hands[self.player_index])
            meld_count = len(self.melds[self.player_index])
            expected_hand_size_for_discard = 14 - (meld_count * 3)
            
            if current_hand_size == expected_hand_size_for_discard:
                print("🔧 패 버리기 상태로 설정")
            else:
                print("🔧 패 뽑기가 필요할 수 있음")
        else:
            print("🔧 AI 턴으로 복구")
            self.waiting_for_player = False
            # AI 턴 강제 시작
            self.start_ai_turn()
        
        print(f"🔧 === 게임 상태 복구 완료 ===")
    
    def debug_print_detailed_state(self):
        """상세 디버그 정보 출력"""
        print(f"🔧 === 상세 게임 상태 ===")
        print(f"게임 단계: {self.game_phase}")
        print(f"현재 턴: {self.current_turn} ({self.player_names[self.current_turn]})")
        print(f"턴 카운터: {self.turn_counter}")
        print(f"waiting_for_player: {self.waiting_for_player}")
        print(f"waiting_for_animation: {self.waiting_for_animation}")
        print(f"drawn_tile: {self.drawn_tile}")
        print(f"pending_action: {self.pending_action}")
        print(f"pending_tile: {self.pending_tile}")
        print(f"action_choices: {len(self.action_choices)}개")
        print(f"discard_animations: {len(self.discard_animations)}개")
        print(f"highlighted_tile: {self.highlighted_tile}")
        
        # 각 플레이어 상태
        for i in range(4):
            hand_size = len(self.hands[i])
            meld_count = len(self.melds[i])
            flower_count = len(self.flower_tiles[i])
            discard_count = len(self.discard_piles[i])
            print(f"  {self.player_names[i]}: 손패={hand_size}, 멜드={meld_count}, 꽃패={flower_count}, 버림패={discard_count}")
        
        print(f"패산 남은 수: {self.wall_manager.get_remaining_tiles_count()}")
        print(f"🔧 === 상세 상태 끝 ===")
    
    def add_discard_animation(self, tile, from_pos, to_pos, player_idx):
        """패 버리기 애니메이션 추가"""
        animation = {
            'tile': tile,
            'from_pos': from_pos,
            'to_pos': to_pos,
            'player_idx': player_idx,
            'start_time': pygame.time.get_ticks(),
            'duration': 400,  # 0.4초로 30% 늦춤 (300ms -> 400ms)
            'active': True
        }
        self.discard_animations.append(animation)
        print(f"🎬 패 버리기 애니메이션 시작: {tile}")
    
    def update_discard_animations(self):
        """패 버리기 애니메이션 업데이트"""
        current_time = pygame.time.get_ticks()
        completed_animations = []
        
        for i, anim in enumerate(self.discard_animations):
            if not anim['active']:
                continue
                
            elapsed = current_time - anim['start_time']
            if elapsed >= anim['duration']:
                anim['active'] = False
                completed_animations.append(i)
        
        # 완료된 애니메이션 제거
        for i in reversed(completed_animations):
            del self.discard_animations[i]
        
        # 모든 애니메이션이 완료되고 콜백이 있으면 실행
        if self.waiting_for_animation and len(self.discard_animations) == 0 and self.animation_callback:
            print("🎬 애니메이션 완료, 콜백 실행")
            callback = self.animation_callback
            self.waiting_for_animation = False
            self.animation_callback = None
            callback()
    
    def get_discard_animation_position(self, anim):
        """패 버리기 애니메이션의 현재 위치 계산 - 더 직선화된 포물선"""
        current_time = pygame.time.get_ticks()
        elapsed = current_time - anim['start_time']
        progress = min(1.0, elapsed / anim['duration'])
        
        # 시작점과 끝점
        start_x, start_y = anim['from_pos']
        end_x, end_y = anim['to_pos']
        
        # 선형 보간으로 x, y 위치 계산
        current_x = start_x + (end_x - start_x) * progress
        current_y = start_y + (end_y - start_y) * progress
        
        # 포물선 효과를 더 약하게 적용 (높이를 30픽셀로 줄임)
        arc_height = 30  # 기존 60에서 30으로 줄임
        arc_offset = arc_height * math.sin(math.pi * progress)
        current_y -= arc_offset
        
        return (int(current_x), int(current_y))
    
    def render_discard_animations(self):
        """패 버리기 애니메이션 렌더링 - 개선된 포물선 애니메이션"""
        for anim in self.discard_animations:
            if not anim['active']:
                continue
                
            current_pos = self.get_discard_animation_position(anim)
            
            # 애니메이션 진행도 계산
            current_time = pygame.time.get_ticks()
            elapsed = current_time - anim['start_time']
            progress = min(1.0, elapsed / anim['duration'])
            
            # 크기 변화 (시작: 원래 크기, 끝: 작아짐)
            start_size = TILE_SIZE
            end_size = (36, 48)  # 버림패 크기
            current_width = int(start_size[0] + (end_size[0] - start_size[0]) * progress)
            current_height = int(start_size[1] + (end_size[1] - start_size[1]) * progress)
            
            # 패 이미지 가져오기 및 크기 조정
            tile_image = self.resources.get_tile_surface(anim['tile'], TILE_SIZE)
            if tile_image:
                # 플레이어별 회전 각도 결정 (회전 없이 원래 모양 유지)
                player_idx = anim['player_idx']
                
                # 플레이어 위치에 따른 패 방향 결정
                if player_idx == 0:  # 플레이어 (하단) - 세로
                    rotated_surface = pygame.transform.scale(tile_image, (current_width, current_height))
                elif player_idx == 1:  # AI1 (우측) - 가로 (90도 회전)
                    rotated_surface = pygame.transform.rotate(tile_image, -90)
                    rotated_surface = pygame.transform.scale(rotated_surface, (current_height, current_width))
                elif player_idx == 2:  # AI2 (상단) - 세로 (180도 회전)
                    rotated_surface = pygame.transform.rotate(tile_image, 180)
                    rotated_surface = pygame.transform.scale(rotated_surface, (current_width, current_height))
                elif player_idx == 3:  # AI3 (좌측) - 가로 (270도 회전)
                    rotated_surface = pygame.transform.rotate(tile_image, 90)
                    rotated_surface = pygame.transform.scale(rotated_surface, (current_height, current_width))
                else:
                    # 기본값 (세로)
                    rotated_surface = pygame.transform.scale(tile_image, (current_width, current_height))
                
                # 중심점 계산하여 렌더링
                rotated_rect = rotated_surface.get_rect(center=current_pos)
                self.screen.blit(rotated_surface, rotated_rect)


    def render_winning_dialog(self):
        """화료 다이얼로그 렌더링 - 개선된 UI와 동적 배치"""
        if not self.winning_dialog_active or not self.winning_yaku_info:
            return
        
        # 반투명 배경
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # 론한 패 하이라이트 (다이얼로그 뒤에서)
        if self.winning_result_type == "ron" and hasattr(self, 'ron_tile'):
            self.discard_manager.set_tile_highlight(self.ron_tile, self.discard_piles, self.screen_to_player)
            self.discard_manager.render_tile_highlights(self.discard_piles, self.screen_to_player)
        
        # 다이얼로그 패널 크기 조정 (역이 많을 때를 위해 높이 증가)
        panel_width = 600
        panel_height = 420  # 350 → 420으로 증가 (글씨 두 줄 정도 더 들어갈 공간)
        
        # 동적 배치 - 버림패 더미를 가리지 않도록
        panel_x = (SCREEN_WIDTH - panel_width) // 2
        panel_y = 60  # 80 → 60으로 조정하여 더 많은 공간 확보
        
        # 패널 배경
        pygame.draw.rect(self.screen, (40, 40, 40), (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, (255, 215, 0), (panel_x, panel_y, panel_width, panel_height), 4)  # 금색 테두리
        
        # 제목 (작은 크기)
        winner_name = self.player_names[self.winning_player_idx]
        result_text = "쯔모!" if self.winning_result_type == "tsumo" else "론!"
        title_text = f"[화료] {winner_name} {result_text}"
        
        title_surface = self.resources.render_text_with_emoji(title_text, "medium", (255, 215, 0))
        title_x = panel_x + (panel_width - title_surface.get_width()) // 2
        title_y = panel_y + 15
        self.screen.blit(title_surface, (title_x, title_y))
        
        current_y = title_y + 30  # 40 → 30으로 줄임
        
        # 화료한 플레이어의 패를 상단에 표시 (버림패 크기)
        if self.winning_yaku_info.get('hand') or self.winning_yaku_info.get('melds'):
            hand_title = f"[완성패] {winner_name}의 완성패"
            hand_title_surface = self.resources.render_text_with_emoji(hand_title, "small", COLORS["highlight"])
            hand_title_x = panel_x + (panel_width - hand_title_surface.get_width()) // 2
            self.screen.blit(hand_title_surface, (hand_title_x, current_y))
            current_y += 20  # 25 → 20으로 줄임
            
            # 패 표시 (버림패 크기)
            tile_size = TILE_SIZE_DISCARD  # 버림패 크기 사용
            start_x = panel_x + 20
            current_x = start_x
            
            # 멜드 먼저 표시
            melds = self.winning_yaku_info.get('melds', [])
            for meld in melds:
                meld_tiles = meld.get('tiles', [])
                meld_type_text = {'peng': '펑', 'ming_gang': '명깡', 'an_gang': '암깡', 'jia_gang': '가깡'}.get(meld['type'], meld['type'])
                
                # 멜드 타입 표시 (더 아래로)
                type_surface = self.resources.render_text_with_emoji(f"[{meld_type_text}]", "small", COLORS["highlight"])
                self.screen.blit(type_surface, (current_x, current_y - 18))
                
                # 멜드 패들 표시 (더 아래로)
                meld_y = current_y + 5  # 패를 더 아래로
                for j, tile in enumerate(meld_tiles):
                    # 암깡의 경우 첫째(0)와 네째(3) 패만 보여주고, 둘째(1)와 세째(2)는 뒷면
                    if meld['type'] == 'an_gang' and j in [1, 2]:
                        # 뒷면 렌더링
                        back_surface = self.create_ai_back_surface(tile_size)
                        self.screen.blit(back_surface, (current_x, meld_y))
                    else:
                        # 일반 패 렌더링
                        tile_surface = self.resources.get_tile_surface(tile, tile_size)
                        self.screen.blit(tile_surface, (current_x, meld_y))
                    current_x += tile_size[0] + 1
                current_x += 8  # 멜드 간 간격
            
            # 손패 표시
            hand = self.winning_yaku_info.get('hand', [])
            if hand:
                if melds:  # 멜드가 있으면 구분선
                    separator_surface = self.resources.render_text_with_emoji("|", "small", COLORS["text"])
                    self.screen.blit(separator_surface, (current_x, current_y + 15))
                    current_x += 15
                
                for tile in hand:
                    tile_surface = self.resources.get_tile_surface(tile, tile_size)
                    self.screen.blit(tile_surface, (current_x, meld_y if melds else current_y))
                    current_x += tile_size[0] + 1
            
            # 론한 패 별도 표시
            if self.winning_result_type == "ron" and hasattr(self, 'ron_tile'):
                current_x += 10
                ron_label = self.resources.render_text_with_emoji("[론]", "small", (255, 100, 100))
                self.screen.blit(ron_label, (current_x, current_y - 18))
                
                ron_tile_surface = self.resources.get_tile_surface(self.ron_tile, tile_size)
                # 론한 패에 빨간 테두리
                ron_y = meld_y if melds else current_y
                pygame.draw.rect(self.screen, (255, 100, 100), (current_x, ron_y, tile_size[0], tile_size[1]), 3)
                self.screen.blit(ron_tile_surface, (current_x, ron_y))
            
            current_y += tile_size[1] + 20  # 더 많은 간격
        
        # 론 시 가져온 패 정보 표시 (작게)
        if self.winning_yaku_info.get('ron_tile_info'):
            ron_info = self.winning_yaku_info['ron_tile_info']
            ron_text = f"[론] {ron_info['from_player_name']}의 {ron_info['tile']}로 론!"
            ron_surface = self.resources.render_text_with_emoji(ron_text, "small", COLORS["highlight"])
            ron_x = panel_x + (panel_width - ron_surface.get_width()) // 2
            self.screen.blit(ron_surface, (ron_x, current_y))
            current_y += 25
        
        # AI 패 공개는 이미 위에서 처리했으므로 제거
        
        # 더 많은 간격 추가
        current_y += 15
        
        # 역 정보 표시 (작게)
        yaku_title = self.resources.render_text_with_emoji("[역] 완성된 역", "small", COLORS["highlight"])
        yaku_title_x = panel_x + (panel_width - yaku_title.get_width()) // 2
        self.screen.blit(yaku_title, (yaku_title_x, current_y))
        current_y += 25
        
        yaku_list = self.winning_yaku_info['yaku_list']
        if yaku_list:
            for i, yaku in enumerate(yaku_list):
                yaku_text = f"• {yaku}"
                yaku_surface = self.resources.render_text_with_emoji(yaku_text, "small", COLORS["text"])
                yaku_x = panel_x + 30
                self.screen.blit(yaku_surface, (yaku_x, current_y))
                current_y += 22  # 18 → 22로 증가 (역 정보 행간 증가)
        else:
            no_yaku_text = "• 역 없음 (기본 화료)"
            no_yaku_surface = self.resources.render_text_with_emoji(no_yaku_text, "small", COLORS["text"])
            no_yaku_x = panel_x + 30
            self.screen.blit(no_yaku_surface, (no_yaku_x, current_y))
            current_y += 22  # 18 → 22로 증가 (역 정보 행간 증가)
        
        current_y += 15  # 더 많은 간격
        
        # 점수 정보 (한국 마작 기준) - 작게
        points_title = self.resources.render_text_with_emoji("[점수] 점수 계산", "small", COLORS["highlight"])
        points_title_x = panel_x + (panel_width - points_title.get_width()) // 2
        self.screen.blit(points_title, (points_title_x, current_y))
        current_y += 25
        
        # 점수 세부 계산 - 통합된 계산 함수 사용
        is_menzen = self.winning_yaku_info.get('is_menzen', True)
        flower_count = self.winning_yaku_info['flower_count']
        is_tsumo = (self.winning_result_type == "tsumo")
        
        # 겐쇼 점수 포함하여 계산
        gensho_count = self.winning_yaku_info.get('gensho_count', 0)
        
        # 통합된 점수 계산 함수 사용
        from mahjong_game import calculate_korean_mahjong_points
        total_points = calculate_korean_mahjong_points(yaku_list, flower_count, is_tsumo, is_menzen, gensho_count)
        
        # 점수 세부 분해 (UI 표시용)
        if is_tsumo:
            base_points = 10  # 쯔모: 10점
        elif not is_menzen:
            base_points = 2   # 멘젠이 깨진 상태: 2점
        else:
            base_points = 5   # 론 (멘젠): 5점
        
        # 역 점수 계산 (표시용)
        gensho_bonus = gensho_count if is_tsumo else 0
        yaku_bonus = total_points - base_points - flower_count - gensho_bonus
        
        # 멘젠쯔모 보너스 (표시용)
        menzen_tsumo_bonus = 0
        if is_tsumo and is_menzen:
            menzen_tsumo_bonus = 2  # 멘젠(1점) + 쯔모(1점) = 2점
            yaku_bonus -= 2  # 이미 total_points에 포함되어 있으므로 차감
        
        # 꽃패 보너스 (표시용)
        flower_bonus = flower_count
        
        points_info = [
            f"기본 점수: {base_points}점",
            f"역 보너스: {yaku_bonus}점 ({len(yaku_list)}역)",
        ]
        
        # 멘젠쯔모 보너스 표시
        if menzen_tsumo_bonus > 0:
            points_info.append(f"멘젠쯔모: {menzen_tsumo_bonus}점 (멘젠1점+쯔모1점)")
        
        # 겐쇼 보너스 표시
        if gensho_bonus > 0:
            points_info.append(f"겐쇼: {gensho_bonus}점 (자뽑 {gensho_bonus}장)")
        
        # 꽃패 보너스 표시
        if flower_bonus > 0:
            points_info.append(f"꽃패 보너스: {flower_bonus}점 ({flower_bonus}장)")
        
        points_info.append(f"총 점수: {total_points}점")
        
        for i, info in enumerate(points_info):
            color = COLORS["highlight"] if i == len(points_info) - 1 else COLORS["text"]
            info_surface = self.resources.render_text_with_emoji(info, "small", color)
            info_x = panel_x + 30
            self.screen.blit(info_surface, (info_x, current_y))
            current_y += 22  # 18 → 22로 증가 (점수 정보 행간 증가)
        
        # 안내 메시지 (작게) - 패널 높이에 맞춰 조정
        guide_text = "클릭하여 계속..."
        guide_surface = self.resources.render_text_with_emoji(guide_text, "small", COLORS["highlight"])
        guide_x = panel_x + (panel_width - guide_surface.get_width()) // 2
        guide_y = panel_y + panel_height - 30  # 패널 높이 증가에 맞춰 조정
        self.screen.blit(guide_surface, (guide_x, guide_y))

    def render_tenpai_dialog(self):
        """간방 옵션 다이얼로그 렌더링"""
        # 간방 옵션이 있으면 옵션 다이얼로그, 없으면 기본 대기패 다이얼로그
        if hasattr(self, 'tenpai_options') and self.tenpai_options:
            self.render_tenpai_options_dialog()
        elif hasattr(self, 'tenpai_waiting_tiles') and self.tenpai_waiting_tiles:
            self.render_simple_tenpai_dialog()
    
    def render_tenpai_options_dialog(self):
        """간방 옵션 다이얼로그 렌더링 - 버릴패와 대기패 함께 표시"""
        if not hasattr(self, 'tenpai_options') or not self.tenpai_options:
            return
        
        # 반투명 배경
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(120)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # 다이얼로그 패널 크기 (옵션 수에 따라 동적 조정)
        option_count = len(self.tenpai_options)
        panel_width = 650  # 더 넓게
        base_height = 200
        option_height = 80  # 각 옵션당 높이
        panel_height = base_height + (option_count * option_height)
        
        panel_x = (SCREEN_WIDTH - panel_width) // 2
        panel_y = (SCREEN_HEIGHT - panel_height) // 2
        
        # 패널 배경
        pygame.draw.rect(self.screen, (40, 60, 40), (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, (100, 255, 100), (panel_x, panel_y, panel_width, panel_height), 3)  # 녹색 테두리
        
        # 제목
        title_text = "[간방 옵션] 어떤 패를 버릴까요?"
        title_surface = self.resources.render_text_with_emoji(title_text, "medium", (100, 255, 100))
        title_x = panel_x + (panel_width - title_surface.get_width()) // 2
        title_y = panel_y + 15
        self.screen.blit(title_surface, (title_x, title_y))
        
        current_y = title_y + 40
        
        # 설명 텍스트
        desc_text = f"패를 버려서 간방 상태로 만들 수 있는 옵션들 ({option_count}가지):"
        desc_surface = self.resources.render_text_with_emoji(desc_text, "small", COLORS["text"])
        desc_x = panel_x + (panel_width - desc_surface.get_width()) // 2
        self.screen.blit(desc_surface, (desc_x, current_y))
        current_y += 35
        
        # 각 옵션 표시
        tile_size = (30, 45)  # 더 작은 크기
        
        for i, option in enumerate(self.tenpai_options):
            option_y = current_y + i * option_height
            
            # 옵션 배경 (약간 어두운 녹색)
            option_bg = pygame.Surface((panel_width - 20, option_height - 5))
            option_bg.set_alpha(100)
            option_bg.fill((20, 40, 20))
            self.screen.blit(option_bg, (panel_x + 10, option_y))
            
            # 옵션 번호와 설명
            option_text = f"{i+1}. {option['discard_name']} 버리기 → 대기패 {option['waiting_count']}개"
            option_surface = self.resources.render_text_with_emoji(option_text, "small", (150, 255, 150))
            self.screen.blit(option_surface, (panel_x + 20, option_y + 5))
            
            # 버릴 패 이미지
            discard_surface = self.resources.get_tile_surface(option['discard_tile'], tile_size)
            discard_x = panel_x + 20
            discard_y = option_y + 25
            self.screen.blit(discard_surface, (discard_x, discard_y))
            
            # 화살표
            arrow_surface = self.resources.render_text_with_emoji("→", "small", (255, 255, 100))
            arrow_x = discard_x + tile_size[0] + 10
            arrow_y = discard_y + tile_size[1] // 2 - arrow_surface.get_height() // 2
            self.screen.blit(arrow_surface, (arrow_x, arrow_y))
            
            # 대기패들 이미지 (최대 8개까지)
            waiting_tiles = option['waiting_tiles'][:8]  # 최대 8개만 표시
            wait_start_x = arrow_x + arrow_surface.get_width() + 10
            
            for j, waiting_tile in enumerate(waiting_tiles):
                wait_x = wait_start_x + j * (tile_size[0] + 3)
                wait_surface = self.resources.get_tile_surface(waiting_tile, tile_size)
                self.screen.blit(wait_surface, (wait_x, discard_y))
                
                # 패 이름 (작게)
                from mahjong_game import get_tile_base_name
                wait_name = get_tile_base_name(waiting_tile)
                name_surface = self.resources.render_text_with_emoji(wait_name, "small", COLORS["text"])
                name_x = wait_x + (tile_size[0] - name_surface.get_width()) // 2
                name_y = discard_y + tile_size[1] + 2
                self.screen.blit(name_surface, (name_x, name_y))
            
            # 대기패가 8개보다 많으면 "..." 표시
            if len(option['waiting_tiles']) > 8:
                more_text = f"... 외 {len(option['waiting_tiles']) - 8}개"
                more_surface = self.resources.render_text_with_emoji(more_text, "small", COLORS["text"])
                more_x = wait_start_x + 8 * (tile_size[0] + 3)
                more_y = discard_y + tile_size[1] // 2
                self.screen.blit(more_surface, (more_x, more_y))
        
        # 안내 메시지
        guide_text = "클릭하여 닫기..."
        guide_surface = self.resources.render_text_with_emoji(guide_text, "small", (100, 255, 100))
        guide_x = panel_x + (panel_width - guide_surface.get_width()) // 2
        guide_y = panel_y + panel_height - 30
        self.screen.blit(guide_surface, (guide_x, guide_y))
    
    def render_simple_tenpai_dialog(self):
        """간단한 간방 상태 대기패 다이얼로그 렌더링"""
        if not hasattr(self, 'tenpai_waiting_tiles') or not self.tenpai_waiting_tiles:
            return
        
        # 반투명 배경
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(120)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # 다이얼로그 패널 크기
        panel_width = 450
        panel_height = 280
        panel_x = (SCREEN_WIDTH - panel_width) // 2
        panel_y = (SCREEN_HEIGHT - panel_height) // 2
        
        # 패널 배경
        pygame.draw.rect(self.screen, (40, 60, 40), (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, (100, 255, 100), (panel_x, panel_y, panel_width, panel_height), 3)  # 녹색 테두리
        
        # 제목
        title_text = "[간방] 화료 대기 상태"
        title_surface = self.resources.render_text_with_emoji(title_text, "medium", (100, 255, 100))
        title_x = panel_x + (panel_width - title_surface.get_width()) // 2
        title_y = panel_y + 15
        self.screen.blit(title_surface, (title_x, title_y))
        
        current_y = title_y + 40
        
        # 설명 텍스트
        desc_text = "다음 패 중 하나가 나오면 화료할 수 있습니다:"
        desc_surface = self.resources.render_text_with_emoji(desc_text, "small", COLORS["text"])
        desc_x = panel_x + (panel_width - desc_surface.get_width()) // 2
        self.screen.blit(desc_surface, (desc_x, current_y))
        current_y += 30
        
        # 대기패 표시 (실제 마작패 이미지로)
        tile_size = TILE_SIZE_DISCARD  # 작은 크기 사용
        tiles_per_row = 6  # 한 줄에 6개씩
        tile_spacing = 5
        
        start_x = panel_x + 20
        current_x = start_x
        current_row = 0
        
        for i, waiting_tile in enumerate(self.tenpai_waiting_tiles):
            if i > 0 and i % tiles_per_row == 0:
                # 다음 줄로
                current_row += 1
                current_x = start_x
                current_y += tile_size[1] + 10
            
            # 대기패 이미지 렌더링
            tile_surface = self.resources.get_tile_surface(waiting_tile, tile_size)
            self.screen.blit(tile_surface, (current_x, current_y))
            
            # 패 이름 표시 (패 아래)
            from mahjong_game import get_tile_base_name
            tile_name = get_tile_base_name(waiting_tile)
            name_surface = self.resources.render_text_with_emoji(tile_name, "small", COLORS["text"])
            name_x = current_x + (tile_size[0] - name_surface.get_width()) // 2
            name_y = current_y + tile_size[1] + 2
            self.screen.blit(name_surface, (name_x, name_y))
            
            current_x += tile_size[0] + tile_spacing
        
        # 안내 메시지
        guide_text = "클릭하여 닫기..."
        guide_surface = self.resources.render_text_with_emoji(guide_text, "small", (100, 255, 100))
        guide_x = panel_x + (panel_width - guide_surface.get_width()) // 2
        guide_y = panel_y + panel_height - 30
        self.screen.blit(guide_surface, (guide_x, guide_y))

if __name__ == "__main__":
    game = MahjongGame()
    game.run() 