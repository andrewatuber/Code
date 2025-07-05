"""
마작 애니메이션 모듈
- 패산 건설 애니메이션
- 배패 애니메이션
- AI 패 버리기 애니메이션
"""

import pygame
import random
import math
from mahjong_resources import DIRECTIONS, TABLE_CENTER_X, TABLE_CENTER_Y


class WallBuildingAnimation:
    """패산 건설 애니메이션"""
    
    def __init__(self, wall_positions):
        self.wall_positions = wall_positions
        self.animation_frame = 0
        self.animation_speed = 8
        self.is_complete = False
        self.current_direction = 0
        self.current_stack = 0
        self.current_layer = 0
        
        # 건설 순서: 북 -> 동 -> 남 -> 서 (시계방향)
        self.build_order = ["북", "동", "남", "서"]
        
    def update(self):
        """애니메이션 업데이트"""
        if self.is_complete:
            return
            
        self.animation_frame += 1
        
        if self.animation_frame % self.animation_speed == 0:
            self._place_next_tile()
    
    def _place_next_tile(self):
        """다음 타일 배치"""
        # 현재 방향이 남(하단)이면 건설하지 않고 넘어감
        current_dir = self.build_order[self.current_direction]
        if current_dir == "남":
            self._next_direction()
            return
            
        if current_dir not in self.wall_positions:
            self._next_direction()
            return
            
        positions = self.wall_positions[current_dir]
        
        if self.current_stack < len(positions):
            # 현재 스택의 다음 층 배치
            self.current_layer += 1
            
            # 2층까지 쌓았으면 다음 스택으로
            if self.current_layer >= 2:
                self.current_layer = 0
                self.current_stack += 1
        else:
            # 다음 방향으로
            self._next_direction()
    
    def _next_direction(self):
        """다음 방향으로 이동"""
        self.current_direction += 1
        self.current_stack = 0
        self.current_layer = 0
        
        if self.current_direction >= len(self.build_order):
            self.is_complete = True
    
    def get_visible_tiles(self):
        """현재 보이는 타일들 반환"""
        visible = {}
        
        for dir_idx in range(self.current_direction + 1):
            if dir_idx >= len(self.build_order):
                break
                
            direction = self.build_order[dir_idx]
            if direction == "남":  # 하단은 건설하지 않음
                continue
                
            if direction not in self.wall_positions:
                continue
                
            positions = self.wall_positions[direction]
            visible[direction] = []
            
            # 이전 방향들은 완전히 완성
            if dir_idx < self.current_direction:
                stack_count = len(positions)
            else:
                # 현재 방향은 부분 완성
                stack_count = self.current_stack
                if self.current_layer > 0:
                    stack_count += 1
            
            visible[direction] = stack_count
            
        return visible


class DealingAnimation:
    """배패 애니메이션"""
    
    def __init__(self, wall_start_position, deal_order):
        self.wall_start_position = wall_start_position
        self.deal_order = deal_order
        self.animation_step = 0
        self.animation_frame = 0
        self.animation_speed = 15
        self.current_round = 0
        self.max_rounds = 3
        self.current_player_idx = 0
        self.current_tile_in_group = 0
        self.is_complete = False
        
        # 현재 애니메이션 중인 타일 정보
        self.current_tile = None
        self.current_start_pos = None
        self.current_end_pos = None
        self.current_direction = None
        
    def start_tile_animation(self, tile, direction, start_pos, end_pos):
        """개별 타일 애니메이션 시작"""
        self.current_tile = tile
        self.current_direction = direction
        self.current_start_pos = start_pos
        self.current_end_pos = end_pos
        self.animation_step = 0
        
    def update(self):
        """애니메이션 업데이트"""
        if self.is_complete:
            return False
            
        if self.current_tile:
            self.animation_step += 1
            
            if self.animation_step >= self.animation_speed:
                # 타일 애니메이션 완료
                self._complete_current_tile()
                return True
        
        return False
    
    def _complete_current_tile(self):
        """현재 타일 애니메이션 완료"""
        self.current_tile = None
        self.current_tile_in_group += 1
        
        if self.current_tile_in_group >= 4:
            # 한 그룹(4장) 완료
            self.current_tile_in_group = 0
            self.current_player_idx += 1
            
            if self.current_player_idx >= 4:
                # 한 라운드 완료
                self.current_player_idx = 0
                self.current_round += 1
                
                if self.current_round >= self.max_rounds:
                    self.is_complete = True
    
    def get_current_tile_position(self):
        """현재 타일의 애니메이션 위치 계산"""
        if not self.current_tile or not self.current_start_pos or not self.current_end_pos:
            return None
            
        progress = self.animation_step / self.animation_speed
        progress = min(1.0, progress)
        
        # 포물선 궤적 계산
        start_x, start_y = self.current_start_pos
        end_x, end_y = self.current_end_pos
        
        # 중간점에서 위로 호를 그리기
        mid_x = start_x + (end_x - start_x) * progress
        arc_height = 50 * math.sin(math.pi * progress)
        mid_y = start_y + (end_y - start_y) * progress - arc_height
        
        return (int(mid_x), int(mid_y))


class DiscardAnimation:
    """패 버리기 애니메이션"""
    
    def __init__(self, tile, direction, start_pos, end_pos):
        self.tile = tile
        self.direction = direction
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.animation_frame = 0
        self.animation_speed = 20
        self.is_complete = False
        
    def update(self):
        """애니메이션 업데이트"""
        if self.is_complete:
            return False
            
        self.animation_frame += 1
        
        if self.animation_frame >= self.animation_speed:
            self.is_complete = True
            return True
            
        return False
    
    def get_current_position(self):
        """현재 위치 계산"""
        if self.is_complete:
            return self.end_pos
            
        progress = self.animation_frame / self.animation_speed
        start_x, start_y = self.start_pos
        end_x, end_y = self.end_pos
        
        current_x = start_x + (end_x - start_x) * progress
        current_y = start_y + (end_y - start_y) * progress
        
        return (int(current_x), int(current_y))
    
    def get_rotation(self):
        """회전각 계산 (방향에 따라)"""
        rotation_map = {
            "동": 270,  # 우측 AI
            "남": 180,  # 하단 플레이어
            "서": 90,   # 좌측 AI
            "북": 0     # 상단 AI
        }
        return rotation_map.get(self.direction, 0)


class AnimationManager:
    """애니메이션 매니저"""
    
    def __init__(self):
        self.wall_building = None
        self.dealing = None
        self.discard_animations = []
        
    def start_wall_building(self, wall_positions):
        """패산 건설 애니메이션 시작"""
        self.wall_building = WallBuildingAnimation(wall_positions)
        
    def start_dealing(self, wall_start_position, deal_order):
        """배패 애니메이션 시작"""
        self.dealing = DealingAnimation(wall_start_position, deal_order)
        
    def start_discard(self, tile, direction, start_pos, end_pos):
        """패 버리기 애니메이션 시작"""
        discard_anim = DiscardAnimation(tile, direction, start_pos, end_pos)
        self.discard_animations.append(discard_anim)
        return discard_anim
        
    def update(self):
        """모든 애니메이션 업데이트"""
        # 패산 건설 애니메이션
        if self.wall_building and not self.wall_building.is_complete:
            self.wall_building.update()
            
        # 배패 애니메이션
        if self.dealing and not self.dealing.is_complete:
            self.dealing.update()
            
        # 버리기 애니메이션들
        completed_discards = []
        for i, discard_anim in enumerate(self.discard_animations):
            if discard_anim.update():
                completed_discards.append(i)
                
        # 완료된 애니메이션 제거
        for i in reversed(completed_discards):
            del self.discard_animations[i]
    
    def is_wall_building_complete(self):
        """패산 건설 완료 여부"""
        return self.wall_building is None or self.wall_building.is_complete
        
    def is_dealing_complete(self):
        """배패 완료 여부"""
        return self.dealing is None or self.dealing.is_complete
        
    def has_active_animations(self):
        """활성 애니메이션 존재 여부"""
        return (
            (self.wall_building and not self.wall_building.is_complete) or
            (self.dealing and not self.dealing.is_complete) or
            len(self.discard_animations) > 0
        ) 