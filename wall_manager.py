import pygame
from mahjong_resources import TABLE_CENTER_X, TABLE_CENTER_Y, TILE_SIZE_DISCARD, SCREEN_WIDTH, SCREEN_HEIGHT

class WallManager:
    """한국 마작 패산 관리자 - 정확한 패산 뽑기 방식 구현"""
    
    def __init__(self, wall_tiles, screen):
        self.wall_tiles = wall_tiles  # 104장의 패 리스트
        self.screen = screen
        
        # 패산 구조: 4면 × 13스택 × 2층 = 104장
        self.STACKS_PER_WALL = 13
        self.LAYERS_PER_STACK = 2
        self.TOTAL_WALLS = 4
        
        # 마작 방향 시계방향 순서 (고정)
        self.MAHJONG_CLOCKWISE_ORDER = ['동', '남', '서', '북']
        
        # 화면 위치 시계방향 순서 (테이블 중심 관점: 상단→우측→하단→좌측)
        self.SCREEN_CLOCKWISE_ORDER = ['top', 'right', 'bottom', 'left']
        
        # 화면 중심에서 각 플레이어를 바라보는 관점: 시계방향 스택 진행
        # 상단: 왼쪽→오른쪽 (0→12) - 작동함
        # 우측: 위→아래 (0→12) - 작동함  
        # 하단: 오른쪽→왼쪽 (12→0) - 수정 필요
        # 좌측: 아래→위 (12→0) - 수정 필요
        self.SCREEN_STACK_DIRECTIONS = {
            'top': (0, 12, 1),     # 상단: 왼쪽→오른쪽 (0→12)
            'right': (0, 12, 1),   # 우측: 위→아래 (0→12)
            'bottom': (12, 0, -1), # 하단: 오른쪽→왼쪽 (12→0)
            'left': (12, 0, -1)    # 좌측: 아래→위 (12→0)
        }
        
        # 동가 위치에 따른 방향 매핑 (게임 시작시 설정됨)
        self.direction_to_screen = {}
        self.screen_to_direction = {}
        
        # 패산 상태 추적
        self.wall_state = {}  # {(wall, stack, layer): tile_index}
        self.dealt_tiles = set()  # 뽑힌 패의 인덱스들
        
        # 현재 뽑기 위치 추적
        self.current_wall = None      # 현재 뽑고 있는 면 ('동', '남', '서', '북')
        self.current_stack = None     # 현재 뽑고 있는 스택 (0~12)
        self.current_layer = None     # 현재 뽑고 있는 층 (0=아래층, 1=위층)
        
        # 왕패 뽑기 위치 추적 (꽃패 보충용)
        self.wang_wall = None
        self.wang_stack = None
        self.wang_layer = None
        
        self._initialize_wall_state()
    
    def _initialize_wall_state(self):
        """패산 상태 초기화 - 화면 시계방향 순서로 패 배치"""
        # 이 메서드는 set_dice_start_position에서 매핑이 설정된 후 호출되어야 함
        pass
    
    def _setup_wall_state_with_mapping(self):
        """매핑 설정 후 패산 상태 초기화"""
        tile_index = 0
        
        # 화면 시계방향 순서로 패 배치 (상단→우측→하단→좌측)
        # 각 면은 화면 중심에서 바라본 관점으로 왼쪽(0)→오른쪽(12) 순서
        for screen_pos in self.SCREEN_CLOCKWISE_ORDER:
            wall_name = self.screen_to_direction.get(screen_pos)
            if wall_name:
                for stack in range(self.STACKS_PER_WALL):
                    for layer in range(self.LAYERS_PER_STACK):
                        self.wall_state[(wall_name, stack, layer)] = tile_index
                        tile_index += 1
    
    def set_dice_start_position(self, dice_sum, player_directions):
        """주사위 합과 플레이어 방향 정보로 시작 위치 설정
        
        Args:
            dice_sum: 주사위 두 개의 합 (2~12)
            player_directions: {'bottom': '동', 'left': '남', 'top': '서', 'right': '북'}
        """
        print(f"[DEBUG] 주사위 합: {dice_sum}, 플레이어 방향: {player_directions}")
        
        # 동가 위치에 따른 방향 매핑 설정
        self.screen_to_direction = player_directions.copy()
        self.direction_to_screen = {v: k for k, v in player_directions.items()}
        
        # 매핑 설정 후 패산 상태 초기화
        self._setup_wall_state_with_mapping()
        
        # 동가 화면 위치 찾기
        east_screen_pos = self.direction_to_screen['동']
        east_screen_index = self.SCREEN_CLOCKWISE_ORDER.index(east_screen_pos)
        
        # 주사위 합으로 시작 화면 위치 결정 (동가부터 화면 시계방향으로 카운트)
        start_screen_index = (east_screen_index + dice_sum - 1) % 4
        start_screen_pos = self.SCREEN_CLOCKWISE_ORDER[start_screen_index]
        start_wall = self.screen_to_direction[start_screen_pos]
        
        # 주사위 합으로 시작 스택 결정 (화면 위치별 시계방향 고려)
        base_stack = (dice_sum - 1) % self.STACKS_PER_WALL
        start_stack = self._get_actual_start_stack(start_screen_pos, base_stack)
        
        # 일반패 뽑기 시작 위치 설정
        self.current_wall = start_wall
        self.current_stack = start_stack
        self.current_layer = 1  # 위층부터 시작
        
        # 왕패 뽑기 시작 위치 설정 (일반패의 정확한 반대 방향)
        self.wang_wall = self.current_wall
        self.wang_stack = self.current_stack
        self.wang_layer = 1  # 2층(위층)부터 시작
        
        # 일반패 시작 위치에서 반시계방향으로 한 위치 이전으로 이동
        self._move_wang_to_counter_clockwise_previous()
        
        print(f"[DEBUG] 일반패 시작: {self.current_wall}면 {self.current_stack}스택 {self.current_layer}층")
        print(f"[DEBUG] 왕패 시작: {self.wang_wall}면 {self.wang_stack}스택 {self.wang_layer}층")
    
    def _get_actual_start_stack(self, screen_pos, base_stack):
        """화면 위치별 시계방향을 고려한 실제 시작 스택 계산"""
        start, end, direction = self.SCREEN_STACK_DIRECTIONS[screen_pos]
        
        if direction > 0:  # 증가 방향 (상단, 우측)
            result = start + base_stack
            return min(result, end)  # end를 넘지 않도록 제한
        else:  # 감소 방향 (하단, 좌측)
            result = start - base_stack
            return max(result, end)  # end 이상으로 제한
    
    def draw_regular_tile(self):
        """일반 패산에서 패 뽑기 - 한국 마작 방식"""
        if len(self.dealt_tiles) >= len(self.wall_tiles):
            print(f"[DEBUG] 모든 패가 뽑힘")
            return None
        
        # 현재 위치에서 패 뽑기
        max_attempts = 104  # 무한루프 방지
        for attempt in range(max_attempts):
            # 현재 위치의 패 확인
            pos_key = (self.current_wall, self.current_stack, self.current_layer)
            if pos_key not in self.wall_state:
                print(f"[DEBUG] 잘못된 위치: {pos_key}")
                return None
            
            tile_index = self.wall_state[pos_key]
            
            # 이미 뽑힌 패가 아니면 뽑기
            if tile_index not in self.dealt_tiles:
                tile = self.wall_tiles[tile_index]
                self.dealt_tiles.add(tile_index)
                
                print(f"[DEBUG] 일반패 뽑음: {self.current_wall}면 {self.current_stack}스택 {self.current_layer}층 → {tile} (인덱스={tile_index})")
                
                # 다음 위치로 이동
                self._advance_regular_position()
                return tile, tile_index
            
            # 이미 뽑힌 패면 다음 위치로 이동
            self._advance_regular_position()
        
        print(f"[DEBUG] 일반패 뽑기 실패 - 최대 시도 횟수 초과")
        return None
    
    def draw_wang_tile(self):
        """왕패에서 패 뽑기 (꽃패 보충용) - 한국 마작 방식"""
        if len(self.dealt_tiles) >= len(self.wall_tiles):
            print(f"[DEBUG] 모든 패가 뽑힘")
            return None
        
        # 현재 위치에서 패 뽑기
        max_attempts = 200  # 무한루프 방지
        for attempt in range(max_attempts):
            # 현재 위치의 패 확인
            pos_key = (self.wang_wall, self.wang_stack, self.wang_layer)
            if pos_key not in self.wall_state:
                print(f"[DEBUG] 잘못된 왕패 위치: {pos_key}")
                return None
            
            tile_index = self.wall_state[pos_key]
            
            # 이미 뽑힌 패가 아니면 뽑기
            if tile_index not in self.dealt_tiles:
                tile = self.wall_tiles[tile_index]
                self.dealt_tiles.add(tile_index)
                
                print(f"[DEBUG] 왕패 뽑음: {self.wang_wall}면 {self.wang_stack}스택 {self.wang_layer}층 → {tile} (인덱스={tile_index})")
                
                # 다음 위치로 이동
                self._advance_wang_position()
                return tile, tile_index
            
            # 이미 뽑힌 패면 다음 위치로 이동
            self._advance_wang_position()
        
        print(f"[DEBUG] 왕패 뽑기 실패 - 최대 시도 횟수 초과")
        return None
    
    def _advance_regular_position(self):
        """일반패 뽑기 위치를 다음으로 이동 (2층→1층→다음스택 2층→1층...)"""
        if self.current_layer == 1:
            # 위층에서 아래층으로
            self.current_layer = 0
        else:
            # 아래층에서 다음 스택의 위층으로
            self.current_layer = 1
            
            # 현재 면에서 다음 스택으로 이동
            next_stack = self._get_next_stack_in_wall(self.current_wall, self.current_stack)
            
            if next_stack is not None:
                # 같은 면 내에서 다음 스택으로 이동
                self.current_stack = next_stack
            else:
                # 현재 면이 끝났으므로 다음 면으로 이동
                self._move_to_next_wall()
                self.current_stack = self._get_first_stack_in_wall(self.current_wall)
    
    def _get_next_stack_in_wall(self, wall, current_stack):
        """현재 면에서 시계방향으로 다음 스택 반환 (None이면 면 끝)"""
        screen_pos = self.direction_to_screen[wall]
        start, end, direction = self.SCREEN_STACK_DIRECTIONS[screen_pos]
        
        next_stack = current_stack + direction
        
        if direction > 0:  # 증가 방향
            return next_stack if next_stack <= end else None
        else:  # 감소 방향
            return next_stack if next_stack >= end else None
    
    def _get_first_stack_in_wall(self, wall):
        """각 면의 시계방향 첫 번째 스택 반환"""
        screen_pos = self.direction_to_screen[wall]
        start, end, direction = self.SCREEN_STACK_DIRECTIONS[screen_pos]
        return start
    
    def _advance_wang_position(self):
        """왕패 뽑기 위치를 다음으로 이동 (일반패의 정확한 반대 - 반시계방향)"""
        if self.wang_layer == 1:
            # 위층에서 아래층으로
            self.wang_layer = 0
        else:
            # 아래층에서 이전 스택의 위층으로 (반시계방향)
            self.wang_layer = 1
            
            # 현재 면에서 반시계방향으로 이전 스택으로 이동
            prev_stack = self._get_counter_clockwise_prev_stack(self.wang_wall, self.wang_stack)
            
            if prev_stack is not None:
                # 같은 면 내에서 이전 스택으로 이동
                self.wang_stack = prev_stack
            else:
                # 현재 면이 끝났으므로 이전 면으로 이동 (반시계방향)
                self._move_wang_to_counter_clockwise_prev_wall()
                new_stack = self._get_counter_clockwise_last_stack(self.wang_wall)
                
                # 스택 범위 검증
                if 0 <= new_stack <= 12:
                    self.wang_stack = new_stack
                else:
                    print(f"[DEBUG] 왕패 스택 범위 오류: {new_stack}, 0으로 설정")
                    self.wang_stack = 0
    
    def _get_counter_clockwise_prev_stack(self, wall, current_stack):
        """현재 면에서 반시계방향으로 이전 스택 반환 (None이면 면 끝)"""
        screen_pos = self.direction_to_screen[wall]
        start, end, direction = self.SCREEN_STACK_DIRECTIONS[screen_pos]
        
        # 반시계방향이므로 방향을 반대로
        wang_direction = -direction
        prev_stack = current_stack + wang_direction
        
        if wang_direction > 0:  # 증가 방향
            return prev_stack if prev_stack <= end else None
        else:  # 감소 방향
            return prev_stack if prev_stack >= start else None
    
    def _get_counter_clockwise_last_stack(self, wall):
        """각 면의 반시계방향 마지막 스택 반환"""
        screen_pos = self.direction_to_screen[wall]
        start, end, direction = self.SCREEN_STACK_DIRECTIONS[screen_pos]
        
        # 반시계방향이므로 시계방향의 반대 끝점부터 시작
        # 시계방향이 start→end라면, 반시계방향은 end→start
        return end if direction > 0 else start
    
    def _move_to_next_wall(self):
        """다음 면으로 이동 (화면 시계방향)"""
        current_screen_pos = self.direction_to_screen[self.current_wall]
        current_index = self.SCREEN_CLOCKWISE_ORDER.index(current_screen_pos)
        next_index = (current_index + 1) % 4
        next_screen_pos = self.SCREEN_CLOCKWISE_ORDER[next_index]
        self.current_wall = self.screen_to_direction[next_screen_pos]
        print(f"[DEBUG] 다음 면으로 이동: {self.current_wall}")
    
    def _move_wang_to_counter_clockwise_prev_wall(self):
        """왕패 이전 면으로 이동 (화면 반시계방향)"""
        current_screen_pos = self.direction_to_screen[self.wang_wall]
        current_index = self.SCREEN_CLOCKWISE_ORDER.index(current_screen_pos)
        prev_index = (current_index - 1) % 4
        prev_screen_pos = self.SCREEN_CLOCKWISE_ORDER[prev_index]
        self.wang_wall = self.screen_to_direction[prev_screen_pos]
        print(f"[DEBUG] 왕패 이전 면으로 이동: {self.wang_wall}")
    
    def _move_wang_to_counter_clockwise_previous(self):
        """왕패 위치를 일반패 시작 위치에서 반시계방향으로 한 위치 이전으로 이동"""
        print(f"[DEBUG] 왕패 초기 위치 조정 시작: {self.wang_wall}면 {self.wang_stack}스택")
        
        # 현재 면에서 반시계방향으로 이전 스택으로 이동
        prev_stack = self._get_counter_clockwise_prev_stack(self.wang_wall, self.wang_stack)
        
        if prev_stack is not None:
            # 같은 면 내에서 이전 스택으로 이동
            self.wang_stack = prev_stack
            print(f"[DEBUG] 같은 면 내 이전 스택으로 이동: {self.wang_stack}")
        else:
            # 현재 면이 끝났으므로 이전 면으로 이동 (반시계방향)
            print(f"[DEBUG] 면 끝 도달, 이전 면으로 이동")
            self._move_wang_to_counter_clockwise_prev_wall()
            new_stack = self._get_counter_clockwise_last_stack(self.wang_wall)
            
            # 스택 범위 검증
            if 0 <= new_stack <= 12:
                self.wang_stack = new_stack
            else:
                print(f"[DEBUG] 왕패 초기 스택 범위 오류: {new_stack}, 12로 설정")
                self.wang_stack = 12
            print(f"[DEBUG] 새 면의 마지막 스택: {self.wang_stack}")
        
        print(f"[DEBUG] 왕패 초기 위치 조정 완료: {self.wang_wall}면 {self.wang_stack}스택")
    
    def get_remaining_tiles_count(self):
        """남은 패 수 반환"""
        return len(self.wall_tiles) - len(self.dealt_tiles)
    
    def is_tile_dealt(self, wall, stack, layer):
        """특정 위치의 패가 뽑혔는지 확인"""
        pos_key = (wall, stack, layer)
        if pos_key not in self.wall_state:
            return True  # 잘못된 위치는 뽑힌 것으로 간주
        
        tile_index = self.wall_state[pos_key]
        return tile_index in self.dealt_tiles
    
    def render_wall(self, player_directions):
        """패산 렌더링 - 현재 패산 상태 기반"""
        remaining_tiles = self.get_remaining_tiles_count()
        if remaining_tiles <= 0:
            return
        
        # 각 화면 위치별로 패산 렌더링
        for screen_pos in ['bottom', 'top', 'left', 'right']:
            wall_direction = self.screen_to_direction.get(screen_pos)
            if wall_direction:
                self._render_wall_side(screen_pos, wall_direction)
    
    def _render_wall_side(self, screen_pos, wall_direction):
        """특정 면의 패산 렌더링"""
        wall_tile_size = TILE_SIZE_DISCARD
        stacks_per_side = self.STACKS_PER_WALL
        
        # 화면 위치별 렌더링 좌표 계산
        if screen_pos == 'bottom':
            start_x = TABLE_CENTER_X - (stacks_per_side * (wall_tile_size[0] + 1)) // 2
            start_y = SCREEN_HEIGHT - 220
            dx, dy = wall_tile_size[0] + 1, 0
            rotate_angle = 0
        elif screen_pos == 'top':
            start_x = TABLE_CENTER_X - (stacks_per_side * (wall_tile_size[0] + 1)) // 2
            start_y = 125
            dx, dy = wall_tile_size[0] + 1, 0
            rotate_angle = 0
        elif screen_pos == 'right':
            # 좌측과 대칭으로 우측 패산 위치 설정
            start_x = SCREEN_WIDTH - 280 - wall_tile_size[1]  # 좌측 280과 대칭
            start_y = TABLE_CENTER_Y - (stacks_per_side * (wall_tile_size[0] + 1)) // 2 - (wall_tile_size[0] // 2)
            dx, dy = 0, wall_tile_size[0] + 1
            rotate_angle = 90
        elif screen_pos == 'left':
            start_x = 280
            start_y = TABLE_CENTER_Y - (stacks_per_side * (wall_tile_size[0] + 1)) // 2 - (wall_tile_size[0] // 2)
            dx, dy = 0, wall_tile_size[0] + 1
            rotate_angle = -90
        
        # 각 스택 렌더링
        for stack_idx in range(stacks_per_side):
            stack_x = start_x + stack_idx * dx
            stack_y = start_y + stack_idx * dy
            
            for layer in range(2):
                # 해당 위치의 패가 뽑혔는지 확인
                if self.is_tile_dealt(wall_direction, stack_idx, layer):
                    continue  # 뽑힌 패는 렌더링하지 않음
                
                # 패 렌더링
                tile_x = stack_x - layer * 2
                tile_y = stack_y - layer * 4
                
                # 패산 색상 및 패턴
                color_idx = (stack_idx + layer) % 6
                wall_color = self._get_wall_color(color_idx)
                
                tile_surface = pygame.Surface(wall_tile_size)
                tile_surface.fill(wall_color)
                pygame.draw.rect(tile_surface, (30, 30, 30), tile_surface.get_rect(), 2)
                
                # 패턴 추가
                pattern_size = 4
                for px in range(3):
                    for py in range(4):
                        pattern_x = 8 + px * 10
                        pattern_y = 8 + py * 10
                        if pattern_x < wall_tile_size[0] - 8 and pattern_y < wall_tile_size[1] - 8:
                            pattern_rect = pygame.Rect(pattern_x, pattern_y, pattern_size, pattern_size)
                            pygame.draw.rect(tile_surface, (200, 200, 200), pattern_rect)
                
                # 그림자 효과 (아래층만)
                if layer == 0:
                    shadow_surface = pygame.Surface(wall_tile_size)
                    shadow_surface.fill((20, 20, 20))
                    shadow_surface.set_alpha(80)
                    if rotate_angle != 0:
                        shadow_surface = pygame.transform.rotate(shadow_surface, rotate_angle)
                    self.screen.blit(shadow_surface, (tile_x + 3, tile_y + 3))
                
                # 회전 적용
                if rotate_angle != 0:
                    tile_surface = pygame.transform.rotate(tile_surface, rotate_angle)
                
                self.screen.blit(tile_surface, (tile_x, tile_y))
    
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
    
    def get_debug_info(self):
        """디버그 정보 반환"""
        return {
            'remaining_tiles': self.get_remaining_tiles_count(),
            'dealt_tiles': len(self.dealt_tiles),
            'current_position': f"{self.current_wall}면 {self.current_stack}스택 {self.current_layer}층",
            'wang_position': f"{self.wang_wall}면 {self.wang_stack}스택 {self.wang_layer}층"
        } 