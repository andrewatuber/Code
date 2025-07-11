import pygame
from mahjong_resources import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, TILE_SIZE_DISCARD

class ActionDialogManager:
    """액션 선택 다이얼로그 관리 클래스"""
    
    def __init__(self, screen, resources):
        self.screen = screen
        self.resources = resources
        self.is_visible = False
        self.actions = []
        self.buttons = []
        self.dialog_rect = None
        self.target_tile = None  # 펑/깡할 대상 패
        
        # 다이얼로그 위치 설정 (화면 더 우측 아래)
        self.dialog_x = SCREEN_WIDTH - 350  # 250에서 350으로 변경 (더 큰 다이얼로그)
        self.dialog_y = SCREEN_HEIGHT - 220  # 180에서 220으로 변경 (더 큰 다이얼로그)
    
    def get_font(self, size):
        """한글 지원 폰트 반환"""
        # 시스템에서 사용 가능한 한글 폰트 찾기
        available_fonts = pygame.font.get_fonts()
        korean_fonts = ['applegothic', 'applesdgothicneo', 'nanumgothic', 'malgungothic', 'gulim', 'arial']
        
        for candidate in korean_fonts:
            for font in available_fonts:
                if candidate in font.lower():
                    try:
                        test_font = pygame.font.SysFont(font, size)
                        test_surface = test_font.render("한글", True, (255, 255, 255))
                        if test_surface.get_width() > 10:
                            return test_font
                    except:
                        continue
        
        # 모든 한글 폰트 실패 시 기본 폰트
        try:
            return pygame.font.Font(None, size)
        except:
            return pygame.font.SysFont('arial', size)
    
    def render_text(self, text, size_type="normal", color=None):
        """
        중앙화된 텍스트 렌더링 함수
        
        Args:
            text: 렌더링할 텍스트
            size_type: 텍스트 크기 타입 ("large", "normal", "small")
            color: 텍스트 색상 (기본값: 흰색)
            
        Returns:
            (surface, rect): 렌더링된 텍스트 surface와 rect
        """
        # 크기 매핑 (텍스트 크기 증가)
        size_map = {
            "large": 18,      # 큰 텍스트 (11 -> 18)
            "normal": 14,     # 일반 텍스트 (8 -> 14)
            "small": 10       # 작은 텍스트 (6 -> 10)
        }
        
        # 기본값 설정
        if color is None:
            color = (255, 255, 255)  # 흰색
        
        font_size = size_map.get(size_type, size_map["normal"])
        font = self.get_font(font_size)
        
        # 텍스트 렌더링
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()
        
        return text_surface, text_rect
        
    def show_dialog(self, actions, target_tile=None):
        """다이얼로그 표시"""
        self.actions = actions
        self.target_tile = target_tile
        self.is_visible = True
        self._create_buttons()
        
    def hide_dialog(self):
        """다이얼로그 숨기기"""
        self.is_visible = False
        self.actions = []
        self.buttons = []
        self.dialog_rect = None
        self.target_tile = None
        
    def _create_buttons(self):
        """버튼들 생성"""
        self.buttons = []
        button_width = 100  # 버튼 너비 증가 (80 -> 100)
        button_height = 50  # 버튼 높이 증가 (40 -> 50)
        button_spacing = 25  # 버튼 간격 증가 (20 -> 25)
        
        # 패스 버튼 추가
        total_buttons = len(self.actions) + 1
        
        # 다이얼로그 크기 계산 (패 표시 공간 포함)
        total_width = total_buttons * button_width + (total_buttons - 1) * button_spacing + 60  # 여백 증가
        dialog_height = button_height + 140  # 더 많은 여백 (100 -> 140)
        
        # 다이얼로그 배경 영역
        self.dialog_rect = pygame.Rect(self.dialog_x, self.dialog_y, total_width, dialog_height)
        
        # 버튼 위치 계산 (패 표시 아래쪽)
        start_x = self.dialog_x + 30  # 여백 증가 (20 -> 30)
        button_y = self.dialog_y + 85  # 패와 버튼 사이 여백 증가 (70 -> 85)
        
        # 액션 버튼들
        for i, action in enumerate(self.actions):
            button_x = start_x + i * (button_width + button_spacing)
            button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            
            # 액션 이름 한글로 변환
            action_names = {
                'peng': '펑',
                'ming_gang': '명깡',
                'an_gang': '암깡',
                'jia_gang': '가깡',
                'riichi': '리치'
            }
            action_text = action_names.get(action.get('type', action), str(action))
            
            self.buttons.append({
                'rect': button_rect,
                'action': action,
                'text': action_text
            })
        
        # 패스 버튼
        pass_button_x = start_x + len(self.actions) * (button_width + button_spacing)
        pass_button_rect = pygame.Rect(pass_button_x, button_y, button_width, button_height)
        self.buttons.append({
            'rect': pass_button_rect,
            'action': 'pass',
            'text': '패스'
        })
    
    def render(self):
        """다이얼로그 렌더링"""
        if not self.is_visible or not self.dialog_rect:
            return
            
        # 다이얼로그 배경
        pygame.draw.rect(self.screen, (40, 40, 40), self.dialog_rect)
        pygame.draw.rect(self.screen, (200, 200, 200), self.dialog_rect, 2)
        
        # 대상 패 표시
        if self.target_tile:
            tile_x = self.dialog_x + 25  # 15에서 25로 증가
            tile_y = self.dialog_y + 20  # 15에서 20으로 증가
            
            # 패 이미지 렌더링 (AI패 크기로 변경)
            tile_size = TILE_SIZE_DISCARD  # (36, 54) AI패 크기 사용
            tile_surface = self.resources.get_tile_surface(self.target_tile, tile_size)
            self.screen.blit(tile_surface, (tile_x, tile_y))
            
            # 패 이름 표시
            tile_name = self.target_tile.replace('.png', '').split('_')[0]
            text_surface, text_rect = self.render_text(f"{tile_name} 액션:", "large", (255, 255, 255))
            text_x = tile_x + tile_size[0] + 20  # 15에서 20으로 증가
            text_y = tile_y + (tile_size[1] - text_surface.get_height()) // 2
            self.screen.blit(text_surface, (text_x, text_y))
        
        # 버튼들 렌더링
        for i, button in enumerate(self.buttons):
            # 패스 버튼은 다른 색상
            if button['text'] == '패스':
                button_color = (80, 80, 80)
            else:
                button_color = (70, 130, 180)  # 스틸 블루
            
            # 버튼 배경
            pygame.draw.rect(self.screen, button_color, button['rect'])
            pygame.draw.rect(self.screen, (255, 255, 255), button['rect'], 1)
            
            # 버튼 텍스트
            text_surface, text_rect = self.render_text(button['text'], "large", (255, 255, 255))
            text_rect.center = button['rect'].center
            self.screen.blit(text_surface, text_rect)
    
    def handle_click(self, pos):
        """클릭 처리 - 클릭된 버튼의 인덱스 반환, 없으면 -1"""
        if not self.is_visible:
            return -1
            
        for i, button in enumerate(self.buttons):
            if button['rect'].collidepoint(pos):
                return i
                
        return -1
    
    def get_action_at_index(self, index):
        """인덱스에 해당하는 액션 반환"""
        print(f"🔍 get_action_at_index: index={index}, actions_count={len(self.actions)}")
        print(f"🔍 actions: {[action.get('type', action) if isinstance(action, dict) else action for action in self.actions]}")
        
        if index == len(self.actions):  # 패스 버튼
            print(f"🔍 반환: 'pass' (패스 버튼)")
            return 'pass'
        elif 0 <= index < len(self.actions):
            action = self.actions[index]
            print(f"🔍 반환: {action} (액션 버튼)")
            return action
        else:
            print(f"🔍 반환: None (잘못된 인덱스)")
            return None 