"""
마작 게임 로직 모듈
- 패 검증 및 정렬
- 화료 체크 및 역 계산
- 점수 계산
"""

import unicodedata


def get_tile_sort_key(tile):
    """패 정렬을 위한 키 생성 - 만패(1-9) → 통패(1-9) → 삭패(2-9) → 자패(동남서북중발백) 순서"""
    if not tile:
        return (999, 999)
    
    # 정규화
    tile = unicodedata.normalize('NFC', tile)
    
    # 파일명에서 확장자 제거
    if tile.endswith('.png'):
        tile = tile[:-4]
    
    # 만패 (1-9) - 첫 번째 우선순위
    if '만' in tile:
        try:
            num = int(tile[0])
            return (1, num)
        except:
            return (1, 999)
    
    # 통패 (1-9) - 두 번째 우선순위
    elif '통' in tile:
        try:
            num = int(tile[0])
            return (2, num)
        except:
            return (2, 999)
    
    # 삭패 (2-9) - 세 번째 우선순위 (1삭은 꽃패로 처리됨)
    elif '삭' in tile:
        try:
            num = int(tile[0])
            if num == 1:
                # 1삭은 꽃패로 분류 (가장 뒤)
                return (9, 1)
            else:
                return (3, num)
        except:
            return (3, 999)
    
    # 자패 - 네 번째 우선순위
    # 풍패 (동남서북)
    elif tile.startswith('동'):
        return (4, 1)
    elif tile.startswith('남'):
        return (4, 2)
    elif tile.startswith('서'):
        return (4, 3)
    elif tile.startswith('북'):
        return (4, 4)
    
    # 삼원패 (중발백)
    elif tile.startswith('중'):
        return (4, 5)
    elif tile.startswith('발'):
        return (4, 6)
    elif tile.startswith('백'):
        return (4, 7)
    
    # 기존 꽃패 (매난국죽, 춘하추동) - 가장 뒤
    elif '매' in tile or '난' in tile or '국' in tile or '죽' in tile:
        return (9, 2)
    elif '춘' in tile or '하' in tile or '추' in tile:
        return (9, 3)
    
    return (999, 999)


def sort_hand(hand):
    """손패 정렬 (기본 - 하단 플레이어용)"""
    return sorted(hand, key=get_tile_sort_key)


def sort_hand_by_position(hand, player_position):
    """플레이어 위치에 따른 손패 정렬
    
    각 플레이어가 테이블 중앙을 바라보는 관점에서 왼쪽에서 오른쪽으로 정렬:
    - bottom (하단): 왼쪽에서 오른쪽 (기본 정렬)
    - right (우측): 아래에서 위로 (역순 정렬)
    - top (상단): 오른쪽에서 왼쪽 (역순 정렬)
    - left (좌측): 위에서 아래로 (기본 정렬)
    """
    sorted_hand = sorted(hand, key=get_tile_sort_key)
    
    if player_position in ['right', 'top']:
        # 우측과 상단 플레이어는 역순으로 정렬
        return list(reversed(sorted_hand))
    else:
        # 하단과 좌측 플레이어는 기본 정렬
        return sorted_hand


def is_flower_tile(tile):
    """꽃패 여부 확인 - 오직 1삭만 꽃패로 사용"""
    if not tile:
        return False
    
    tile = unicodedata.normalize('NFC', tile)
    if tile.endswith('.png'):
        tile = tile[:-4]
    
    # 오직 1삭만 꽃패로 사용 (다른 패는 모두 일반 패)
    return tile.startswith('1삭')


def normalize_tile_name(tile):
    """패 이름 정규화"""
    if not tile:
        return ""
    
    tile = unicodedata.normalize('NFC', tile)
    if tile.endswith('.png'):
        tile = tile[:-4]
    
    # _숫자 부분 제거 (같은 패의 다른 변형)
    if '_' in tile:
        tile = tile.split('_')[0]
    
    return tile


def count_tile_groups(hand):
    """손패에서 각 패의 개수 계산"""
    tile_count = {}
    for tile in hand:
        normalized = normalize_tile_name(tile)
        tile_count[normalized] = tile_count.get(normalized, 0) + 1
    return tile_count


def check_basic_pattern(hand):
    """기본 마작 패턴 체크 (4 몸통 + 1 머리) - 순자 포함"""
    if len(hand) != 14:
        return False, "패 수가 14장이 아닙니다."
    
    tile_count = count_tile_groups(hand)
    
    # 모든 가능한 머리(2장 쌍) 후보를 시도
    pairs = [tile for tile, count in tile_count.items() if count >= 2]
    
    if not pairs:
        return False, "머리(2장 쌍)가 없습니다. 같은 패 2장이 필요합니다."
    
    # 각 머리 후보에 대해 화료 가능성 체크
    for head_tile in pairs:
        if try_winning_pattern(tile_count.copy(), head_tile):
            return True, f"화료 성공! 머리: {head_tile}(2장)"
    
    # 모든 머리 후보로 화료가 안 되는 경우
    return False, f"화료 실패 - 가능한 머리: {pairs}, 하지만 4개 몸통을 만들 수 없습니다."


def try_winning_pattern(tile_count, head_tile):
    """특정 머리로 4개 몸통을 만들 수 있는지 체크"""
    # 머리 제거
    if tile_count[head_tile] < 2:
        return False
    tile_count[head_tile] -= 2
    if tile_count[head_tile] == 0:
        del tile_count[head_tile]
    
    # 남은 패로 4개 몸통을 만들 수 있는지 체크
    return can_form_melds(tile_count, 4)


def can_form_melds(tile_count, target_melds):
    """주어진 패로 목표 개수의 몸통을 만들 수 있는지 체크"""
    if target_melds == 0:
        return sum(tile_count.values()) == 0
    
    if sum(tile_count.values()) < target_melds * 3:
        return False
    
    # 깊은 복사로 원본 보존
    remaining_tiles = tile_count.copy()
    
    # 1. 먼저 각(같은 패 3장) 찾기
    for tile, count in list(remaining_tiles.items()):
        if count >= 3:
            # 각 제거하고 재귀 호출
            remaining_tiles[tile] -= 3
            if remaining_tiles[tile] == 0:
                del remaining_tiles[tile]
            
            if can_form_melds(remaining_tiles, target_melds - 1):
                return True
            
            # 백트래킹: 원상복구
            remaining_tiles[tile] = remaining_tiles.get(tile, 0) + 3
    
    # 2. 순자(연속된 숫자) 찾기
    for suit in ['만', '통', '삭']:
        for num in range(1, 8):  # 1-2-3부터 7-8-9까지
            tile1 = f"{num}{suit}"
            tile2 = f"{num+1}{suit}"
            tile3 = f"{num+2}{suit}"
            
            if (remaining_tiles.get(tile1, 0) >= 1 and 
                remaining_tiles.get(tile2, 0) >= 1 and 
                remaining_tiles.get(tile3, 0) >= 1):
                
                # 순자 제거하고 재귀 호출
                remaining_tiles[tile1] -= 1
                remaining_tiles[tile2] -= 1
                remaining_tiles[tile3] -= 1
                
                # 0이 된 타일 제거
                for tile in [tile1, tile2, tile3]:
                    if remaining_tiles[tile] == 0:
                        del remaining_tiles[tile]
                
                if can_form_melds(remaining_tiles, target_melds - 1):
                    return True
                
                # 백트래킹: 원상복구
                remaining_tiles[tile1] = remaining_tiles.get(tile1, 0) + 1
                remaining_tiles[tile2] = remaining_tiles.get(tile2, 0) + 1
                remaining_tiles[tile3] = remaining_tiles.get(tile3, 0) + 1
    
    return False


def analyze_hand_composition(hand):
    """손패 구성 분석 (디버깅용)"""
    tile_count = count_tile_groups(hand)
    
    pairs = []      # 2장 쌍
    triplets = []   # 3장 세트  
    quads = []      # 4장 세트
    singles = []    # 1장
    
    for tile, count in tile_count.items():
        if count == 1:
            singles.append(tile)
        elif count == 2:
            pairs.append(tile)
        elif count == 3:
            triplets.append(tile)
        elif count == 4:
            quads.append(tile)
    
    # 가능한 순자 찾기
    possible_sequences = []
    for suit in ['만', '통', '삭']:
        for num in range(1, 8):
            tile1 = f"{num}{suit}"
            tile2 = f"{num+1}{suit}"
            tile3 = f"{num+2}{suit}"
            
            if (tile_count.get(tile1, 0) >= 1 and 
                tile_count.get(tile2, 0) >= 1 and 
                tile_count.get(tile3, 0) >= 1):
                possible_sequences.append(f"{tile1}-{tile2}-{tile3}")
    
    return {
        'pairs': pairs,
        'triplets': triplets, 
        'quads': quads,
        'singles': singles,
        'possible_sequences': possible_sequences
    }


def check_yaku(hand, is_tsumo=False, is_menzen=True, player_wind="동", round_wind="동", flower_count=0):
    """역(役) 체크 - 한국 마작 기준"""
    yaku_list = []
    tile_count = count_tile_groups(hand)
    analysis = analyze_hand_composition(hand)
    
    # 기본 역들
    if is_tsumo and is_menzen:
        yaku_list.append("멘젠쯔모")
    
    # 풍패 관련 역
    if tile_count.get(player_wind, 0) >= 3:
        yaku_list.append(f"자풍 {player_wind}")
    
    if tile_count.get(round_wind, 0) >= 3:
        yaku_list.append(f"장풍 {round_wind}")
    
    # 삼원패 역
    dragon_triplets = 0
    dragon_pairs = 0
    for tile in ["중", "발", "백"]:
        count = tile_count.get(tile, 0)
        if count >= 3:
            dragon_triplets += 1
            yaku_list.append(f"역패 {tile}")
        elif count == 2:
            dragon_pairs += 1
    
    # 대삼원/소삼원
    if dragon_triplets == 3:
        yaku_list.append("대삼원")  # 8점
    elif dragon_triplets == 2 and dragon_pairs == 1:
        yaku_list.append("소삼원")  # 6점
    
    # 사풍패 역
    wind_triplets = 0
    wind_pairs = 0
    for tile in ["동", "남", "서", "북"]:
        count = tile_count.get(tile, 0)
        if count >= 3:
            wind_triplets += 1
        elif count == 2:
            wind_pairs += 1
    
    # 대사희/소사희
    if wind_triplets == 4:
        yaku_list.append("대사희")  # 특수 점수
    elif wind_triplets == 3:
        yaku_list.append("소사희")  # 8점
    
    # 탕야오 (1,9,자패 없음) - 한국 마작에서는 1점
    terminal_honor_tiles = ["1만", "9만", "1통", "9통", "1삭", "9삭", "동", "남", "서", "북", "중", "발", "백"]
    has_terminal_honor = any(tile_count.get(tile, 0) > 0 for tile in terminal_honor_tiles)
    if not has_terminal_honor:
        yaku_list.append("탕야오")
    
    # 핀후 (모든 몸통이 순자, 머리가 역패가 아님) - 한국 마작에서는 1점
    has_triplets = len(analysis['triplets']) > 0 or len(analysis['quads']) > 0
    if not has_triplets and len(analysis['pairs']) == 1:
        head_tile = analysis['pairs'][0]
        if head_tile not in ["동", "남", "서", "북", "중", "발", "백"]:
            # 추가로 순자가 실제로 있는지 확인
            if len(analysis['possible_sequences']) >= 4:
                yaku_list.append("핀후")
    
    # 혼일색/청일색
    suits = ['만', '통', '삭']
    suit_counts = {}
    honor_count = 0
    
    for tile, count in tile_count.items():
        if tile in ["동", "남", "서", "북", "중", "발", "백"]:
            honor_count += count
        else:
            for suit in suits:
                if suit in tile:
                    suit_counts[suit] = suit_counts.get(suit, 0) + count
                    break
    
    active_suits = [suit for suit, count in suit_counts.items() if count > 0]
    if len(active_suits) == 1 and honor_count > 0:
        yaku_list.append("혼일색")  # 2점
    elif len(active_suits) == 1 and honor_count == 0:
        yaku_list.append("청일색")  # 8점
    
    # 일기통관 (1-2-3-4-5-6-7-8-9 한 종류로 완성)
    for suit in suits:
        suit_tiles = [tile for tile in tile_count.keys() if suit in tile]
        if len(suit_tiles) >= 9:
            # 1부터 9까지 모두 있는지 확인
            numbers = set()
            for tile in suit_tiles:
                try:
                    num = int(tile.split(suit)[0])
                    numbers.add(num)
                except:
                    continue
            if numbers == set(range(1, 10)):
                yaku_list.append("일기통관")  # 4점
    
    # 앙꼬 (같은 패 3장) 개수 체크
    triplet_count = len([tile for tile, count in tile_count.items() if count >= 3])
    if triplet_count == 4:
        if is_menzen:
            yaku_list.append("사앙꼬")  # 8점 (멘젠일 때만)
        else:
            yaku_list.append("돌돌이")  # 2점 (멘젠 깨진 상태)
    elif triplet_count == 3:
        if is_menzen:
            yaku_list.append("삼앙꼬")  # 4점 (멘젠일 때만)
    
    # 칠대작 (7가지 서로 다른 자패)
    honor_types = sum(1 for tile in ["동", "남", "서", "북", "중", "발", "백"] if tile_count.get(tile, 0) > 0)
    if honor_types == 7:
        yaku_list.append("칠대작")  # 4점
    
    # 부지부 (문전청 + 쯔모)
    if is_menzen and is_tsumo and not yaku_list:
        yaku_list.append("부지부")  # 5점
    
    # 특수 화료 (천화, 지화, 인화는 게임 로직에서 별도 처리 필요)
    # 구려보등 (9연보등)도 별도 처리 필요
    
    return yaku_list


def calculate_korean_mahjong_points(yaku_list, flower_count=0, is_tsumo=False):
    """한국 마작 점수 계산 - 정확한 점수표"""
    # 기본 점수: 10점
    base_points = 10
    
    # 역별 점수 (한국 마작 기준)
    yaku_points = 0
    for yaku in yaku_list:
        if "탕야오" in yaku or "핀후" in yaku:
            yaku_points += 1
        elif "혼일색" in yaku or "이깡자" in yaku or "돌돌이" in yaku:
            yaku_points += 2
        elif "삼앙꼬" in yaku or "일기통관" in yaku or "칠대작" in yaku:
            yaku_points += 4
        elif "부지부" in yaku:
            yaku_points += 5
        elif "소삼원" in yaku:
            yaku_points += 6
        elif "청일색" in yaku or "대삼원" in yaku or "사앙꼬" in yaku or "소사희" in yaku:
            yaku_points += 8
        elif "천화" in yaku or "지화" in yaku or "인화" in yaku:
            yaku_points += 16
        elif "구려보등" in yaku:
            yaku_points += 24
        elif "자풍" in yaku or "장풍" in yaku or "역패" in yaku:
            yaku_points += 1
        elif "멘젠쯔모" in yaku:
            yaku_points += 1
        else:
            yaku_points += 1  # 기타 역들
    
    # 꽃패 보너스: 1장당 1점
    flower_bonus = flower_count
    
    # 총 점수
    total_points = base_points + yaku_points + flower_bonus
    
    return total_points


def calculate_yaku_points(yaku_list):
    """기존 호환성을 위한 함수 (deprecated)"""
    return len(yaku_list)


def is_winning_hand(hand, is_tsumo=False, is_menzen=True, player_wind="동", round_wind="동", flower_count=0):
    """화료 가능 여부 체크"""
    print("=== 🎯 화료 체크 시작 ===")
    print(f"패 목록: {hand}")
    print(f"패 수: {len(hand)}장")
    print(f"꽃패: {flower_count}장")
    print(f"쯔모: {is_tsumo}, 멘젠: {is_menzen}, 플레이어 바람: {player_wind}")
    
    # 패 구성 분석
    tile_count = count_tile_groups(hand)
    print(f"📋 패 구성: {tile_count}")
    
    # 상세 분석 정보
    analysis = analyze_hand_composition(hand)
    print("🔍 분석 결과:")
    print(f"   머리(2장): {analysis['pairs']}")
    print(f"   몸통(3장+): {analysis['triplets']}")
    print(f"   깡(4장): {analysis['quads']}")
    print(f"   가능한 순자: {analysis['possible_sequences']}")
    print(f"   꽃패: {flower_count}장")
    
    # 기본 패턴 체크 (순자 포함)
    is_valid, message = check_basic_pattern(hand)
    
    if not is_valid:
        print(f"❌ 화료 실패 - {message}")
        print("=== 🎯 화료 체크 완료 ===")
        return False
    
    # 역 체크 (꽃패 포함)
    yaku_list = check_yaku(hand, is_tsumo, is_menzen, player_wind, round_wind, flower_count)
    
    if not yaku_list:
        print("❌ 화료 실패 - 역(役)이 없습니다")
        print("=== 🎯 화료 체크 완료 ===")
        return False
    
    print(f"✅ 화료 성공! 역: {', '.join(yaku_list)}")
    print("=== 🎯 화료 체크 완료 ===")
    return True


def can_ron_with_tile(hand, tile, player_wind="동", round_wind="동"):
    """론 가능 여부 체크"""
    test_hand = hand + [tile]
    return is_winning_hand(test_hand, is_tsumo=False, is_menzen=True, player_wind=player_wind, round_wind=round_wind)


def can_pon(hand, tile):
    """펑 가능 여부 체크 - 손패에 같은 패 2장이 있는지"""
    print(f"[펑 체크] 버려진 패: {tile} -> 기본명: {normalize_tile_name(tile)}")
    
    target_tile = normalize_tile_name(tile)
    matching_tiles = []
    
    for hand_tile in hand:
        if normalize_tile_name(hand_tile) == target_tile:
            matching_tiles.append(hand_tile)
    
    print(f"[펑 체크] 손패에서 {target_tile} 개수: {len(matching_tiles)}개")
    print(f"[펑 체크] 매칭 패들: {matching_tiles}")
    
    can_do_pon = len(matching_tiles) >= 2
    print(f"[펑 체크] 펑 가능: {can_do_pon}")
    
    return can_do_pon


def can_kan(hand, tile):
    """깡 가능 여부 체크"""
    target_tile = normalize_tile_name(tile)
    matching_count = sum(1 for hand_tile in hand if normalize_tile_name(hand_tile) == target_tile)
    return matching_count >= 3


def get_closed_kan_opportunities(hand):
    """암깡 가능한 패들 찾기"""
    tile_count = count_tile_groups(hand)
    kan_opportunities = []
    
    for tile, count in tile_count.items():
        if count == 4:
            kan_opportunities.append(tile)
    
    return kan_opportunities 