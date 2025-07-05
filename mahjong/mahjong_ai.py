"""
마작 AI 로직 모듈
- AI 패 선택 및 버리기
- AI 반응 결정 (펑/깡/론)
- AI 전략
"""

import random
from mahjong_game import normalize_tile_name, can_pon, can_kan, is_winning_hand


def ai_choose_discard(hand, direction="AI"):
    """AI가 버릴 패 선택"""
    if not hand:
        return None
    
    print(f"AI {direction} 패 선택 중... (손패: {len(hand)}장)")
    
    # 간단한 AI 로직: 자패(풍패, 삼원패) 우선 버리기
    honor_tiles = []
    number_tiles = []
    
    for tile in hand:
        normalized = normalize_tile_name(tile)
        if any(wind in normalized for wind in ["동", "남", "서", "북", "중", "발", "백"]):
            honor_tiles.append(tile)
        else:
            number_tiles.append(tile)
    
    # 1순위: 자패 중 무작위 선택
    if honor_tiles:
        return random.choice(honor_tiles)
    
    # 2순위: 수패 중 무작위 선택
    if number_tiles:
        return random.choice(number_tiles)
    
    # 최후: 아무 패나
    return random.choice(hand)


def calculate_ai_pon_chance(hand, tile, direction="AI"):
    """AI의 펑 확률 계산"""
    if not can_pon(hand, tile):
        return 0.0
    
    # 기본 펑 확률 50%
    base_chance = 0.5
    
    # 손패가 적으면 펑 확률 증가
    if len(hand) <= 10:
        base_chance += 0.2
    
    # 자패는 펑 확률 낮춤
    normalized = normalize_tile_name(tile)
    if any(wind in normalized for wind in ["동", "남", "서", "북", "중", "발", "백"]):
        base_chance -= 0.3
    
    return max(0.0, min(1.0, base_chance))


def calculate_ai_kan_chance(hand, tile, direction="AI"):
    """AI의 깡 확률 계산"""
    if not can_kan(hand, tile):
        return 0.0
    
    # 깡은 펑보다 확률 낮춤
    base_chance = 0.3
    
    # 손패가 많으면 깡 확률 증가
    if len(hand) >= 12:
        base_chance += 0.2
    
    return max(0.0, min(1.0, base_chance))


def calculate_ai_ron_chance(hand, tile, direction="AI"):
    """AI의 론 확률 계산"""
    # 실제 화료 가능 여부 체크
    test_hand = hand + [tile]
    
    # 방향에 따른 플레이어 바람 설정
    wind_map = {"동": "동", "남": "남", "서": "서", "북": "북"}
    player_wind = wind_map.get(direction, "동")
    
    if is_winning_hand(test_hand, is_tsumo=False, is_menzen=True, player_wind=player_wind):
        return 1.0  # 화료 가능하면 100% 론
    
    return 0.0


def should_ai_react(hand, tile, direction="AI"):
    """AI가 반응할지 결정"""
    reactions = []
    
    # 론 체크 (최우선)
    ron_chance = calculate_ai_ron_chance(hand, tile, direction)
    if ron_chance > 0 and random.random() < ron_chance:
        reactions.append("론")
    
    # 깡 체크
    kan_chance = calculate_ai_kan_chance(hand, tile, direction)
    if kan_chance > 0 and random.random() < kan_chance:
        reactions.append("깡")
    
    # 펑 체크
    pon_chance = calculate_ai_pon_chance(hand, tile, direction)
    if pon_chance > 0 and random.random() < pon_chance:
        reactions.append("펑")
    
    # 우선순위: 론 > 깡 > 펑
    if "론" in reactions:
        return "론"
    elif "깡" in reactions:
        return "깡"
    elif "펑" in reactions:
        return "펑"
    
    return None


def ai_analyze_hand(hand):
    """AI 손패 분석"""
    from mahjong_game import count_tile_groups
    
    tile_count = count_tile_groups(hand)
    
    # 패 구성 분석
    pairs = sum(1 for count in tile_count.values() if count == 2)
    triplets = sum(1 for count in tile_count.values() if count == 3)
    quads = sum(1 for count in tile_count.values() if count == 4)
    
    analysis = {
        'pairs': pairs,
        'triplets': triplets,
        'quads': quads,
        'total_sets': triplets + quads,
        'hand_strength': pairs + triplets * 2 + quads * 3
    }
    
    return analysis


def ai_get_discard_priority(hand):
    """AI 버림패 우선순위 계산"""
    from mahjong_game import count_tile_groups
    
    tile_count = count_tile_groups(hand)
    priorities = {}
    
    for tile in hand:
        normalized = normalize_tile_name(tile)
        priority = 0
        
        # 자패는 높은 우선순위로 버림
        if any(wind in normalized for wind in ["동", "남", "서", "북", "중", "발", "백"]):
            priority += 10
        
        # 고립된 패 (1장뿐인 패)
        if tile_count.get(normalized, 0) == 1:
            priority += 5
        
        # 이미 3장 이상 있는 패의 4번째
        if tile_count.get(normalized, 0) >= 3:
            priority += 8
        
        priorities[tile] = priority
    
    return priorities


def ai_improved_discard(hand, direction="AI"):
    """개선된 AI 버림패 선택"""
    if not hand:
        return None
    
    priorities = ai_get_discard_priority(hand)
    
    # 가장 높은 우선순위의 패들 찾기
    max_priority = max(priorities.values())
    candidates = [tile for tile, priority in priorities.items() if priority == max_priority]
    
    # 후보 중 무작위 선택
    return random.choice(candidates) 