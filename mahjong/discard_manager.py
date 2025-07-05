import pygame
from mahjong_resources import TABLE_CENTER_X, TABLE_CENTER_Y, TILE_SIZE_DISCARD, SCREEN_WIDTH, SCREEN_HEIGHT

class DiscardManager:
    """버림패 그리기와 하이라이트 관리 클래스"""
    
    def __init__(self, screen, resources):
        self.screen = screen
        self.resources = resources
        self.highlighted_tile = None
        self.highlight_positions = []
        
        # 버림패 더미 (4명의 플레이어)
        self.discard_piles = [[] for _ in range(4)]
        
        # 각 패의 정확한 위치를 저장하는 딕셔너리
        # key: (player_idx, tile_index), value: (x, y, rotation)
        self.tile_positions = {}
        
    def get_discard_pile_center(self, player_idx, screen_to_player):
        """버림패 더미의 중앙 위치 반환"""
        pos = self.get_player_screen_position(player_idx, screen_to_player)
        
        discard_areas = {
            "top": {"center_x": TABLE_CENTER_X, "center_y": TABLE_CENTER_Y - 188},
            "right": {"center_x": TABLE_CENTER_X + 120, "center_y": TABLE_CENTER_Y - 24},
            "bottom": {"center_x": TABLE_CENTER_X, "center_y": TABLE_CENTER_Y + 92},
            "left": {"center_x": TABLE_CENTER_X - 168, "center_y": TABLE_CENTER_Y - 24}
        }
        
        if pos in discard_areas:
            area = discard_areas[pos]
            return (area["center_x"], area["center_y"])
        
        return (TABLE_CENTER_X, TABLE_CENTER_Y)
    
    def get_player_screen_position(self, player_idx, screen_to_player):
        """플레이어 인덱스에서 화면 위치 반환"""
        for screen_pos, idx in screen_to_player.items():
            if idx == player_idx:
                return screen_pos
        return "bottom"
    
    def calculate_discard_tile_position(self, screen_pos, tile_index):
        """버림패 더미에서 특정 인덱스의 패 위치 계산"""
        discard_areas = {
            "top": {"center_x": TABLE_CENTER_X, "center_y": TABLE_CENTER_Y - 188, "rotation": 180},
            "right": {"center_x": TABLE_CENTER_X + 120, "center_y": TABLE_CENTER_Y - 24, "rotation": 90},
            "bottom": {"center_x": TABLE_CENTER_X, "center_y": TABLE_CENTER_Y + 92, "rotation": 0},
            "left": {"center_x": TABLE_CENTER_X - 168, "center_y": TABLE_CENTER_Y - 24, "rotation": -90}
        }
        
        if screen_pos not in discard_areas:
            return None
            
        area = discard_areas[screen_pos]
        tile_size = (36, 48)
        tile_spacing = 38
        
        row = tile_index // 6
        col = tile_index % 6
        
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
    
    def render_discard_pile(self, pos, discard_piles, screen_to_player):
        """버림패 더미 렌더링 및 위치 저장"""
        player_idx = screen_to_player.get(pos)
        if player_idx is None:
            return
        
        pile = discard_piles[player_idx]
        if not pile:
            return
        
        discard_areas = {
            "top": {"center_x": TABLE_CENTER_X, "center_y": TABLE_CENTER_Y - 188, "rotation": 180},
            "right": {"center_x": TABLE_CENTER_X + 120, "center_y": TABLE_CENTER_Y - 24, "rotation": 90},
            "bottom": {"center_x": TABLE_CENTER_X, "center_y": TABLE_CENTER_Y + 92, "rotation": 0},
            "left": {"center_x": TABLE_CENTER_X - 168, "center_y": TABLE_CENTER_Y - 24, "rotation": -90}
        }
        
        if pos not in discard_areas:
            return
            
        area = discard_areas[pos]
        tile_size = (36, 48)
        tile_spacing = 38
        
        for i, tile in enumerate(pile):
            row = i // 6
            col = i % 6
            
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
            
            # 패 위치 저장 (하이라이트용)
            self.tile_positions[(player_idx, i)] = (tile_x, tile_y, area["rotation"])
            
            # 패 이미지 렌더링
            tile_surface = self.resources.get_tile_surface(tile, tile_size)
            
            # 회전 적용
            if area["rotation"] != 0:
                tile_surface = pygame.transform.rotate(tile_surface, area["rotation"])
            
            # 중앙 정렬하여 렌더링
            tile_rect = tile_surface.get_rect(center=(tile_x, tile_y))
            self.screen.blit(tile_surface, tile_rect)
    
    def get_discarded_tile_positions(self, tile, discard_piles, screen_to_player):
        """특정 패가 버림패 더미에서 위치한 모든 좌표 반환"""
        positions = []
        
        for player_idx, pile in enumerate(discard_piles):
            screen_pos = self.get_player_screen_position(player_idx, screen_to_player)
            
            for tile_index, discarded_tile in enumerate(pile):
                if discarded_tile == tile:
                    pos = self.calculate_discard_tile_position(screen_pos, tile_index)
                    if pos:
                        positions.append(pos)
        
        return positions
    
    def set_tile_highlight(self, tile, discard_piles, screen_to_player):
        """패 하이라이트 설정 - 저장된 위치 정보 사용"""
        self.highlighted_tile = tile
        self.highlight_positions = []
        
        # 저장된 위치 정보에서 해당 패 찾기
        for player_idx, pile in enumerate(discard_piles):
            for tile_index, discarded_tile in enumerate(pile):
                if discarded_tile == tile:
                    position_key = (player_idx, tile_index)
                    if position_key in self.tile_positions:
                        x, y, rotation = self.tile_positions[position_key]
                        self.highlight_positions.append((x, y, rotation))
                    else:
                        # 백업: 계산된 위치 사용
                        screen_pos = self.get_player_screen_position(player_idx, screen_to_player)
                        pos = self.calculate_discard_tile_position(screen_pos, tile_index)
                        if pos:
                            # 회전 정보 추가
                            discard_areas = {
                                "top": 180, "right": 90, "bottom": 0, "left": -90
                            }
                            rotation = discard_areas.get(screen_pos, 0)
                            self.highlight_positions.append((pos[0], pos[1], rotation))
    
    def clear_tile_highlight(self):
        """패 하이라이트 해제"""
        self.highlighted_tile = None
        self.highlight_positions = []
    
    def render_tile_highlights(self, discard_piles, screen_to_player):
        """패 하이라이트 렌더링 - 개선된 버전"""
        if not self.highlighted_tile or not self.highlight_positions:
            return
        
        for pos_info in self.highlight_positions:
            if isinstance(pos_info, tuple):
                if len(pos_info) == 3:
                    # 새로운 형식: (x, y, rotation)
                    x, y, rotation = pos_info
                elif len(pos_info) == 2:
                    # 이전 형식: (x, y) - 기본 회전값 0
                    x, y = pos_info
                    rotation = 0
                else:
                    continue
                
                # 회전에 따른 하이라이트 크기 결정
                if rotation in [90, -90]:
                    # 90도 회전된 패 - 가로세로 바뀜
                    highlight_surface = pygame.Surface((65, 50), pygame.SRCALPHA)
                    inner_rect = pygame.Rect(4, 4, 57, 42)
                else:
                    # 일반 패 (0도, 180도)
                    highlight_surface = pygame.Surface((50, 65), pygame.SRCALPHA)
                    inner_rect = pygame.Rect(4, 4, 42, 57)
                
                # 노란색 테두리 (두꺼운 테두리)
                pygame.draw.rect(highlight_surface, (255, 255, 0, 180), 
                               highlight_surface.get_rect(), 4)
                
                # 반투명 노란색 배경
                pygame.draw.rect(highlight_surface, (255, 255, 0, 60), inner_rect)
                
                # 중앙 정렬하여 렌더링
                highlight_rect = highlight_surface.get_rect(center=(x, y))
                self.screen.blit(highlight_surface, highlight_rect)
    
    def get_discard_pile_next_position(self, player_idx, discard_piles, screen_to_player):
        """버림패 더미에서 다음 패가 놓일 정확한 위치 계산"""
        pos = self.get_player_screen_position(player_idx, screen_to_player)
        pile = discard_piles[player_idx]
        next_index = len(pile)  # 현재 더미 크기가 다음 인덱스
        
        return self.calculate_discard_tile_position(pos, next_index)
    
    def add_discard_tile(self, player_idx, tile):
        """버림패 추가"""
        self.discard_piles[player_idx].append(tile)
        print(f"🗂️ {player_idx}번 플레이어 버림패 추가: {tile}")
    
    def render_all_discard_piles(self):
        """모든 플레이어의 버림패 더미 렌더링"""
        for player_idx in range(4):
            self.render_discard_pile(player_idx)
    
    def clear_all_discard_piles(self):
        """모든 버림패 더미 초기화"""
        self.discard_piles = [[] for _ in range(4)]
        self.tile_positions = {}  # 위치 정보도 초기화
        print("🗂️ 모든 버림패 더미 초기화") 