from fighter import *

def evaluate_state(ai_fighter, human_fighter):
    """
    Evaluates the current game state from the perspective of the AI.
    Higher score is better for AI.
    """
    score = 0
    
    # HP Advantage
    score += (ai_fighter.hp - human_fighter.hp) * 10
    
    # Stamina Advantage
    score += (ai_fighter.stamina - human_fighter.stamina)
    
    # Coordination Advantage
    score += ai_fighter.coordination * 2
    
    # Distance weighting (AI wants to be in range to attack if it has stamina, or back off if low)
    dist = abs(ai_fighter.x - human_fighter.x)
    if ai_fighter.stamina > 50:
        if dist < 90:
            score += 20 # Good, in attack range
        else:
            score -= 10 # Bad, out of range
    else:
        if dist > 150:
            score += 20 # Good, resting at safe distance
        else:
            score -= 20 # Danger, close with low stamina
            
    return score

def simulate_combat(attacker, defender, l_action, r_action):
    # Simplified combat simulation
    dmg = 0
    kb = 0
    dist = abs(attacker.x - defender.x)
    
    # Very crude approximation of combat simulation for Minimax
    if l_action == ACTION_PUNCH or r_action == ACTION_PUNCH:
        if dist < 70: dmg += 5; kb += 20
    if l_action == ACTION_KICK or r_action == ACTION_KICK:
        if dist < 90: dmg += 8; kb += 30
    if l_action == ACTION_SPECIAL and r_action == ACTION_SPECIAL:
        if dist < 120: dmg += 25; kb += 80
        
    defender.hp -= dmg
    if dmg > 0:
        direction = 1 if attacker.x < defender.x else -1
        defender.x += direction * kb

def minimax(ai_state, human_state, depth, is_maximizing, alpha, beta):
    if depth == 0 or ai_state.hp <= 0 or human_state.hp <= 0:
        return evaluate_state(ai_state, human_state)
        
    possible_actions = [ACTION_IDLE, ACTION_PUNCH, ACTION_KICK, ACTION_BLOCK, ACTION_DODGE]
    
    if is_maximizing:
        max_eval = float('-inf')
        for l_action in possible_actions:
            for r_action in possible_actions:
                # Clone states
                mock_ai = Fighter(ai_state.x, ai_state.y, (0,0,0), 'B')
                mock_ai.hp = ai_state.hp; mock_ai.stamina = ai_state.stamina; mock_ai.coordination = ai_state.coordination
                
                mock_human = Fighter(human_state.x, human_state.y, (0,0,0), 'A')
                mock_human.hp = human_state.hp; mock_human.stamina = human_state.stamina
                
                simulate_combat(mock_ai, mock_human, l_action, r_action)
                
                eval = minimax(mock_ai, mock_human, depth - 1, False, alpha, beta)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = float('inf')
        for l_action in possible_actions:
            for r_action in possible_actions:
                mock_ai = Fighter(ai_state.x, ai_state.y, (0,0,0), 'B')
                mock_ai.hp = ai_state.hp; mock_ai.stamina = ai_state.stamina; mock_ai.coordination = ai_state.coordination
                
                mock_human = Fighter(human_state.x, human_state.y, (0,0,0), 'A')
                mock_human.hp = human_state.hp; mock_human.stamina = human_state.stamina
                
                simulate_combat(mock_human, mock_ai, l_action, r_action)
                
                eval = minimax(mock_ai, mock_human, depth - 1, True, alpha, beta)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            if beta <= alpha:
                break
        return min_eval

def get_best_actions(ai_fighter, human_fighter, depth=2):
    possible_actions = [ACTION_IDLE, ACTION_PUNCH, ACTION_KICK, ACTION_BLOCK, ACTION_DODGE]
    if ai_fighter.coordination == 100:
        possible_actions.append(ACTION_SPECIAL)
        
    best_score = float('-inf')
    best_left = ACTION_IDLE
    best_right = ACTION_IDLE
    
    alpha = float('-inf')
    beta = float('inf')
    
    for l_action in possible_actions:
        for r_action in possible_actions:
            # Clone states
            mock_ai = Fighter(ai_fighter.x, ai_fighter.y, (0,0,0), 'B')
            mock_ai.hp = ai_fighter.hp; mock_ai.stamina = ai_fighter.stamina; mock_ai.coordination = ai_fighter.coordination
            
            mock_human = Fighter(human_fighter.x, human_fighter.y, (0,0,0), 'A')
            mock_human.hp = human_fighter.hp; mock_human.stamina = human_fighter.stamina
            
            simulate_combat(mock_ai, mock_human, l_action, r_action)
            
            score = minimax(mock_ai, mock_human, depth - 1, False, alpha, beta)
            
            if score > best_score:
                best_score = score
                best_left = l_action
                best_right = r_action
                
            alpha = max(alpha, best_score)
            
    return best_left, best_right
