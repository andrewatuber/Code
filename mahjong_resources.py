"""
마작 리소스 관리 모듈
- 이미지 로딩 및 관리
- 폰트 설정
- 색상 정의
- 화면 설정
"""

import pygame
import os
import unicodedata


# 화면 및 게임 설정
SCREEN_WIDTH = 1200  # 1400의 80%
SCREEN_HEIGHT = 900  # 720의 120% (20% 증가)
TABLE_CENTER_X = SCREEN_WIDTH // 2
TABLE_CENTER_Y = SCREEN_HEIGHT // 2

# 타일 크기 설정
TILE_SIZE = (52, 78)           # 플레이어 손패 크기 
TILE_SIZE_DISCARD = (36, 54)   # 버림패 크기 (AI 손패에도 사용)
TILE_SIZE_WALL = (36, 54)      # 패산 크기

# 타일 이미지 경로
TILE_FOLDER = "tiles"
TILE_BACK = "tile_back.png"

# 방향 상수
DIRECTIONS = ["동", "남", "서", "북"]

# 색상 정의
COLORS = {
    "bg": (34, 139, 34),      # 포레스트 그린 (테이블 색상)
    "text": (255, 255, 255),   # 흰색
    "highlight": (255, 215, 0), # 금색
    "red": (255, 0, 0),        # 빨간색
    "wall": (139, 69, 19),     # 갈색 (패산 색상)
    "table_edge": (0, 100, 0), # 어두운 초록 (테이블 테두리)
}


def load_tile_image(tile_path, size=TILE_SIZE):
    """타일 이미지 로드 및 크기 조정"""
    try:
        image = pygame.image.load(tile_path)
        return pygame.transform.scale(image, size)
    except Exception as e:
        print(f"이미지 로드 실패: {tile_path}, 오류: {e}")
        # 플레이스홀더 이미지 생성 (적절한 색상으로)
        placeholder = pygame.Surface(size)
        placeholder.fill((230, 230, 230))  # 밝은 회색
        pygame.draw.rect(placeholder, (100, 100, 100), placeholder.get_rect(), 2)
        # 중앙에 "?" 표시
        font = pygame.font.Font(None, size[1] // 2)
        text_surface = font.render("?", True, (100, 100, 100))
        text_rect = text_surface.get_rect(center=(size[0]//2, size[1]//2))
        placeholder.blit(text_surface, text_rect)
        return placeholder


def create_tile_back_surface(size=TILE_SIZE):
    """타일 뒷면 이미지 생성"""
    surface = pygame.Surface(size)
    surface.fill((139, 69, 19))  # 갈색
    
    # 테두리
    pygame.draw.rect(surface, (0, 0, 0), surface.get_rect(), 2)
    
    # 격자 패턴
    for i in range(0, size[0], 10):
        pygame.draw.line(surface, (160, 82, 45), (i, 0), (i, size[1]), 1)
    for i in range(0, size[1], 10):
        pygame.draw.line(surface, (160, 82, 45), (0, i), (size[0], i), 1)
    
    return surface


def create_dice_surface(number, size=30):
    """주사위 면 생성"""
    surface = pygame.Surface((size, size))
    surface.fill((255, 255, 255))
    pygame.draw.rect(surface, (0, 0, 0), surface.get_rect(), 2)
    
    # 주사위 점 그리기
    dot_size = size // 8
    positions = {
        1: [(size//2, size//2)],
        2: [(size//4, size//4), (3*size//4, 3*size//4)],
        3: [(size//4, size//4), (size//2, size//2), (3*size//4, 3*size//4)],
        4: [(size//4, size//4), (3*size//4, size//4), 
            (size//4, 3*size//4), (3*size//4, 3*size//4)],
        5: [(size//4, size//4), (3*size//4, size//4), (size//2, size//2),
            (size//4, 3*size//4), (3*size//4, 3*size//4)],
        6: [(size//4, size//4), (3*size//4, size//4), 
            (size//4, size//2), (3*size//4, size//2),
            (size//4, 3*size//4), (3*size//4, 3*size//4)]
    }
    
    if number in positions:
        for pos in positions[number]:
            pygame.draw.circle(surface, (0, 0, 0), pos, dot_size)
    
    return surface


class ResourceManager:
    """리소스 관리 클래스"""
    
    def __init__(self):
        self.tile_images = {}
        self.fonts = {}
        self.init_fonts()
        self.load_all_tile_images()
    
    def init_fonts(self):
        """폰트 초기화"""
        pygame.font.init()
        
        # 한글 폰트 우선 시도
        korean_font_loaded = False
        korean_fonts = [
            '/System/Library/Fonts/AppleSDGothicNeo.ttc',  # macOS
            '/System/Library/Fonts/Helvetica.ttc',  # macOS 대체
            'C:/Windows/Fonts/malgun.ttf',  # Windows 맑은 고딕
            'C:/Windows/Fonts/gulim.ttc',   # Windows 굴림
            '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',  # Linux
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'   # Linux 대체
        ]
        
        for font_path in korean_fonts:
            try:
                if os.path.exists(font_path):
                    self.fonts['large'] = pygame.font.Font(font_path, 32)
                    self.fonts['medium'] = pygame.font.Font(font_path, 28)
                    self.fonts['normal'] = pygame.font.Font(font_path, 24)
                    self.fonts['small'] = pygame.font.Font(font_path, 18)
                    print(f"한글 폰트 로드 성공: {font_path}")
                    korean_font_loaded = True
                    break
            except Exception as e:
                print(f"폰트 로드 실패: {font_path} - {e}")
                continue
        
        # 한글 폰트 로드 실패 시 시스템 폰트 사용
        if not korean_font_loaded:
            print("한글 폰트 로드 실패, 시스템 폰트 사용")
            # macOS에서 한글 지원하는 시스템 폰트들 시도
            system_fonts = ['AppleSDGothicNeo-Regular', 'Helvetica', 'Arial Unicode MS', 'Arial']
            
            for font_name in system_fonts:
                try:
                    self.fonts['large'] = pygame.font.SysFont(font_name, 32)
                    self.fonts['medium'] = pygame.font.SysFont(font_name, 28)
                    self.fonts['normal'] = pygame.font.SysFont(font_name, 24)
                    self.fonts['small'] = pygame.font.SysFont(font_name, 18)
                    print(f"시스템 폰트 사용: {font_name}")
                    break
                except Exception as e:
                    continue
            else:
                # 최후의 수단: 기본 폰트
                self.fonts['large'] = pygame.font.Font(None, 32)
                self.fonts['medium'] = pygame.font.Font(None, 28)
                self.fonts['normal'] = pygame.font.Font(None, 24)
                self.fonts['small'] = pygame.font.Font(None, 18)
                print("기본 폰트 사용")
    
    def load_all_tile_images(self):
        """모든 타일 이미지 로드"""
        print("=== 타일 이미지 로딩 시작 ===")
        
        # 타일 뒷면 로드
        back_path = os.path.join(TILE_FOLDER, TILE_BACK)
        if os.path.exists(back_path):
            self.tile_images[TILE_BACK] = load_tile_image(back_path, TILE_SIZE)
            print(f"✓ 타일 뒷면 로딩: {TILE_BACK}")
        else:
            self.tile_images[TILE_BACK] = create_tile_back_surface(TILE_SIZE)
            print(f"✓ 타일 뒷면 생성: {TILE_BACK}")
        
        # 모든 게임 타일 로드
        loaded_count = 0
        
        if not os.path.exists(TILE_FOLDER):
            print(f"❌ 타일 폴더가 없습니다: {TILE_FOLDER}")
            return
        
        try:
            files = os.listdir(TILE_FOLDER)
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    if filename == TILE_BACK:
                        continue
                    
                    file_path = os.path.join(TILE_FOLDER, filename)
                    normalized_filename = unicodedata.normalize('NFC', filename)
                    
                    try:
                        self.tile_images[normalized_filename] = load_tile_image(file_path, TILE_SIZE)
                        loaded_count += 1
                        
                        if loaded_count <= 5:  # 처음 5개만 로그 출력
                            print(f"✓ 로딩: {normalized_filename}")
                        elif loaded_count % 20 == 0:  # 20개마다 진행상황 출력
                            print(f"... {loaded_count}개 로딩 중...")
                    
                    except Exception as e:
                        print(f"❌ 로딩 실패: {filename} - {e}")
            
            print(f"=== 타일 이미지 로딩 완료: 총 {loaded_count + 1}개 ===")
            
            # 타일 뒷면 별칭 추가 (암깡 등에서 사용)
            if TILE_BACK in self.tile_images:
                self.tile_images['back.png'] = self.tile_images[TILE_BACK]
                print(f"✓ 타일 뒷면 별칭 추가: back.png -> {TILE_BACK}")
            
        except Exception as e:
            print(f"타일 폴더 읽기 오류: {e}")
    
    def get_tile_surface(self, tile, target_size):
        """타일 이미지를 가져오는 개선된 함수 - 더 엄격한 로직"""
        if not tile or not isinstance(tile, str):
            return self.create_placeholder_surface(target_size)
        
        # AI 뒷면 특수 처리
        if tile == 'ai_back':
            return self.create_ai_back_surface(target_size)
        
        normalized_tile = unicodedata.normalize('NFC', tile)
        # 파일명에 .png가 없으면 추가
        if not normalized_tile.lower().endswith('.png'):
            normalized_tile += '.png'
            
        if normalized_tile in self.tile_images:
            tile_surface = self.tile_images[normalized_tile]
            if tile_surface.get_size() != target_size:
                return pygame.transform.scale(tile_surface, target_size)
            return tile_surface
        
        # 타일 이름을 찾지 못한 경우 플레이스홀더 반환
        print(f"⚠️ 타일 이미지 못찾음: {normalized_tile}, 플레이스홀더 사용")
        return self.create_placeholder_surface(target_size)
    
    def create_placeholder_surface(self, size, color=None): # color 매개변수는 이제 사용하지 않음
        """플레이스홀더 이미지 생성 - 항상 물음표 표시"""
        placeholder = pygame.Surface(size)
        placeholder.fill((200, 200, 200))  # 밝은 회색 배경
        pygame.draw.rect(placeholder, (100, 100, 100), placeholder.get_rect(), 2) # 테두리
        
        # 중앙에 "?" 표시
        try:
            # 시스템 폰트가 없거나 로드 실패할 경우를 대비
            font_size = min(size[0], size[1]) // 2
            font = pygame.font.Font(None, font_size) # 기본 시스템 폰트
            text_surface = font.render("?", True, (50, 50, 50)) # 어두운 회색 글자
            text_rect = text_surface.get_rect(center=(size[0]//2, size[1]//2))
            placeholder.blit(text_surface, text_rect)
        except Exception as e:
            print(f"플레이스홀더 폰트 로드 실패: {e}")
            # 폰트 로드 실패 시 간단한 X 표시
            pygame.draw.line(placeholder, (50, 50, 50), (size[0]*0.2, size[1]*0.2), (size[0]*0.8, size[1]*0.8), 2)
            pygame.draw.line(placeholder, (50, 50, 50), (size[0]*0.8, size[1]*0.2), (size[0]*0.2, size[1]*0.8), 2)
            
        return placeholder
    
    def create_ai_back_surface(self, size):
        """AI 플레이어용 패 뒷면 생성 (암깡용)"""
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
                if dot_x < size[0] - 6 and dot_y < size[1] - 8:  # 경계 체크
                    pygame.draw.circle(surface, (200, 200, 200), (dot_x, dot_y), 2)
        
        return surface
    
    def render_text_with_emoji(self, text, size="normal", color=(255, 255, 255)):
        """이모지 포함 텍스트 렌더링"""
        # 사이즈 매핑
        size_map = {
            "large": "large",
            "medium": "medium", 
            "normal": "normal",
            "small": "small"
        }
        
        font_key = size_map.get(size, "normal")
        
        try:
            if font_key in self.fonts:
                return self.fonts[font_key].render(text, True, color)
            else:
                # 폴백: 기본 폰트 사용
                return self.fonts['normal'].render(text, True, color)
        except Exception as e:
            print(f"텍스트 렌더링 실패: {text} - {e}")
            # 최후의 수단: 기본 pygame 폰트
            try:
                fallback_font = pygame.font.Font(None, 24)
                return fallback_font.render(str(text), True, color)
            except:
                # 완전 실패 시 빈 서페이스 반환
                surface = pygame.Surface((100, 30))
                surface.fill(color)
                return surface 