#!/usr/bin/env python3
"""
Скрипт для замены всех update.callback_query.edit_message_text на safe_edit_message
"""

import re

def fix_callbacks():
    file_path = "/Users/vlad/Developer/Marha/src/bot.py"
    
    # Читаем файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Заменяем все вызовы edit_message_text на safe_edit_message
    
    # Паттерн 1: await update.callback_query.edit_message_text(
    pattern1 = r'await update\.callback_query\.edit_message_text\('
    replacement1 = 'await safe_edit_message(\n                update.callback_query,'
    
    content = re.sub(pattern1, replacement1, content)
    
    # Паттерн 2: await query.edit_message_text(
    pattern2 = r'await query\.edit_message_text\('
    replacement2 = 'await safe_edit_message(\n                query,'
    
    content = re.sub(pattern2, replacement2, content)
    
    # Паттерн 3: query.edit_message_text( без await
    pattern3 = r'(?<!await )query\.edit_message_text\('
    replacement3 = 'safe_edit_message(\n                query,'
    
    content = re.sub(pattern3, replacement3, content)
    
    # Заменяем query.answer() на safe_answer_callback
    pattern4 = r'await query\.answer\(\)'
    replacement4 = 'await safe_answer_callback(query)'
    
    content = re.sub(pattern4, replacement4, content)
    
    pattern5 = r'await query\.answer\("([^"]+)"\)'
    replacement5 = r'await safe_answer_callback(query, "\1")'
    
    content = re.sub(pattern5, replacement5, content)
    
    pattern6 = r'await update\.callback_query\.answer\(\)'
    replacement6 = 'await safe_answer_callback(update.callback_query)'
    
    content = re.sub(pattern6, replacement6, content)
    
    pattern7 = r'await update\.callback_query\.answer\("([^"]+)"([^)]*)\)'
    replacement7 = r'await safe_answer_callback(update.callback_query, "\1"\2)'
    
    content = re.sub(pattern7, replacement7, content)
    
    # Записываем обратно
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Callbacks исправлены!")

if __name__ == "__main__":
    fix_callbacks()
