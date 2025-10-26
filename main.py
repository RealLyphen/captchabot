from telethon import TelegramClient, events, Button
from PIL import Image, ImageDraw, ImageFont
import random
import string
import io
import json
import os
from datetime import datetime, timedelta
import asyncio
from pathlib import Path

# ==================== CONFIGURATION ====================

API_ID = 24839357
API_HASH = '4c7ac3d774fd95bf81d3924cf012978b'
BOT_TOKEN = '8240894268:AAFX3ORhudkKFqbZfzrYklOhFC23BvHKm-Q'
ADMIN_ID = 7207727106

# File paths
DATA_DIR = Path('bot_data')
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / 'users_data.json'
CAPTCHA_FILE = DATA_DIR / 'captchas.json'
QR_DIR = DATA_DIR / 'qr_codes'
QR_DIR.mkdir(exist_ok=True)

# Initialize bot
bot = TelegramClient('captcha_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# User states
user_states = {}

# ==================== DATA MANAGEMENT ====================

def load_json(file_path, default=None):
    """Load JSON file safely"""
    if default is None:
        default = {}
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
    return default

def save_json(file_path, data):
    """Save JSON file safely"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving {file_path}: {e}")
        return False

def load_data():
    return load_json(DATA_FILE)

def save_data(data):
    return save_json(DATA_FILE, data)

def load_captchas():
    return load_json(CAPTCHA_FILE)

def save_captchas(captchas):
    return save_json(CAPTCHA_FILE, captchas)

def get_user_data(user_id):
    """Get user data or create new user"""
    data = load_data()
    user_id = str(user_id)
    
    if user_id not in data:
        data[user_id] = {
            'balance': 0,
            'completed_captchas': [],
            'last_reset': datetime.now().strftime('%Y-%m-%d'),
            'daily_captcha_count': 0,
            'total_earned': 0,
            'total_withdrawn': 0,
            'successful_withdrawals': 0,
            'failed_attempts': 0,
            'joined_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_active': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_data(data)
    else:
        # Update last active
        data[user_id]['last_active'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_data(data)
    
    return data[user_id]

def update_user_data(user_id, updates):
    """Update specific user data fields"""
    data = load_data()
    user_id = str(user_id)
    if user_id in data:
        data[user_id].update(updates)
        save_data(data)
        return True
    return False

# ==================== TIME MANAGEMENT ====================

def get_next_reset_time():
    """Get next midnight reset time"""
    tomorrow = datetime.now() + timedelta(days=1)
    next_reset = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    return next_reset

def get_time_until_reset():
    """Get time remaining until next reset"""
    next_reset = get_next_reset_time()
    time_left = next_reset - datetime.now()
    
    hours = int(time_left.total_seconds() // 3600)
    minutes = int((time_left.total_seconds() % 3600) // 60)
    seconds = int(time_left.total_seconds() % 60)
    
    return hours, minutes, seconds

def format_time_left():
    """Format time left until reset"""
    hours, minutes, seconds = get_time_until_reset()
    return f"{hours:02d}h {minutes:02d}m"

# ==================== CAPTCHA GENERATION ====================

def generate_text_captcha():
    """Generate random text captcha"""
    random.seed(datetime.now().timestamp() + random.random())
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return text

def create_captcha_image(text):
    """Create enhanced captcha image"""
    width, height = 350, 120
    
    bg_colors = [(240, 240, 245), (245, 245, 250), (235, 240, 245), (250, 248, 245), (245, 250, 250)]
    bg_color = random.choice(bg_colors)
    
    image = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(image)
    
    # Try multiple font paths
    font_paths = [
        "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Windows/Fonts/arial.ttf",
        "C:\\Windows\\Fonts\\arial.ttf"
    ]
    
    font = None
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, 50)
            break
        except:
            continue
    
    if font is None:
        font = ImageFont.load_default()
    
    # Background lines
    for _ in range(12):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        line_color = (random.randint(180, 220), random.randint(180, 220), random.randint(180, 220))
        draw.line([(x1, y1), (x2, y2)], fill=line_color, width=2)
    
    # Draw text
    x_start = 30
    for i, char in enumerate(text):
        y_offset = random.randint(-15, 15)
        rotation = random.randint(-20, 20)
        x_pos = x_start + (i * 50)
        y_pos = 35 + y_offset
        
        char_color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        draw.text((x_pos, y_pos), char, font=font, fill=char_color)
    
    # Noise
    for _ in range(400):
        x, y = random.randint(0, width), random.randint(0, height)
        dot_color = (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200))
        draw.point((x, y), fill=dot_color)
    
    # Circles
    for _ in range(7):
        x = random.randint(0, width)
        y = random.randint(0, height)
        r = random.randint(5, 15)
        circle_color = (random.randint(200, 230), random.randint(200, 230), random.randint(200, 230))
        draw.ellipse([x-r, y-r, x+r, y+r], outline=circle_color, width=1)
    
    img_bytes = io.BytesIO()
    img_bytes.name = 'captcha.png'
    image.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes

def generate_math_captcha():
    """Generate math captcha"""
    random.seed(datetime.now().timestamp() + random.random())
    
    operations = [
        ('addition', '+'),
        ('subtraction', '-'),
        ('multiplication', '×'),
    ]
    
    operation_type, symbol = random.choice(operations)
    
    if operation_type == 'addition':
        num1 = random.randint(10, 99)
        num2 = random.randint(10, 99)
        answer = num1 + num2
        question = f"{num1} + {num2}"
    elif operation_type == 'subtraction':
        num1 = random.randint(30, 99)
        num2 = random.randint(10, num1)
        answer = num1 - num2
        question = f"{num1} - {num2}"
    else:
        num1 = random.randint(2, 15)
        num2 = random.randint(2, 12)
        answer = num1 * num2
        question = f"{num1} × {num2}"
    
    return {
        'question': question,
        'answer': str(answer),
        'type': 'math'
    }

def generate_pattern_captcha():
    """Generate pattern captcha"""
    random.seed(datetime.now().timestamp() + random.random())
    
    patterns = [
        {'question': 'Which one is different?\n🍎 🍎 🍊 🍎', 'answer': '🍊', 'options': ['🍎', '🍊', '🍏', '🍇']},
        {'question': 'Which one is different?\n🚗 🚗 🚗 🚕', 'answer': '🚕', 'options': ['🚗', '🚕', '🚙', '🚐']},
        {'question': 'Which one is different?\n⭐ ⭐ ⭐ 🌟', 'answer': '🌟', 'options': ['⭐', '🌟', '✨', '💫']},
        {'question': 'Which one is different?\n😀 😀 😀 😢', 'answer': '😢', 'options': ['😀', '😢', '😁', '😃']},
        {'question': 'Which animal can fly?\n🐕 🐈 🦅 🐠', 'answer': '🦅', 'options': ['🐕', '🐈', '🦅', '🐠']},
        {'question': 'Which is a fruit?\n🥕 🍕 🍎 🍔', 'answer': '🍎', 'options': ['🥕', '🍕', '🍎', '🍔']},
        {'question': 'What comes next?\n2, 4, 6, 8, ?', 'answer': '10', 'options': ['9', '10', '11', '12']},
        {'question': 'Complete: 🔴 🔵 🔴 🔵 ?', 'answer': '🔴', 'options': ['🔴', '🔵', '🟢', '🟡']},
        {'question': 'Which is cold?\n🔥 ☀️ ❄️ 💡', 'answer': '❄️', 'options': ['🔥', '☀️', '❄️', '💡']},
        {'question': 'Which can swim?\n🐕 🐈 🐟 🐦', 'answer': '🐟', 'options': ['🐕', '🐈', '🐟', '🐦']},
        {'question': 'Which is round?\n⬛ ⬜ 🔵 ⬛', 'answer': '🔵', 'options': ['⬛', '⬜', '🔵', '🔺']},
        {'question': 'Pick the vehicle:\n🍕 🚀 🍎 🌸', 'answer': '🚀', 'options': ['🍕', '🚀', '🍎', '🌸']},
        {'question': 'Which is smallest?\n🐘 🐁 🐈 🐕', 'answer': '🐁', 'options': ['🐘', '🐁', '🐈', '🐕']},
        {'question': 'Which is hot?\n❄️ 🔥 💧 🌊', 'answer': '🔥', 'options': ['❄️', '🔥', '💧', '🌊']},
        {'question': 'Complete: 🌙 ☀️ 🌙 ☀️ ?', 'answer': '🌙', 'options': ['🌙', '☀️', '⭐', '🌟']},
    ]
    
    selected = random.choice(patterns)
    return {
        'question': selected['question'],
        'answer': selected['answer'],
        'options': selected['options'],
        'type': 'pattern'
    }

def generate_word_unscramble():
    """Generate word unscramble"""
    random.seed(datetime.now().timestamp() + random.random())
    
    words = [
        'MONEY', 'PHONE', 'WATER', 'LIGHT', 'HOUSE', 'WORLD', 'MUSIC', 'BRAIN', 'HEART', 'OCEAN',
        'SMART', 'HAPPY', 'EARTH', 'CLOUD', 'TIGER', 'APPLE', 'BREAD', 'CHAIR', 'TABLE', 'CLOCK',
        'DREAM', 'PEACE', 'POWER', 'SMILE', 'TRUST', 'VOICE', 'PLANT', 'STONE', 'RIVER', 'SWEET',
        'BOOKS', 'STARS', 'MAGIC', 'DANCE', 'GRACE', 'FAITH', 'TRUTH', 'BRAVE', 'CLEAN', 'FRESH'
    ]
    
    word = random.choice(words)
    scrambled = ''.join(random.sample(word, len(word)))
    
    attempts = 0
    while scrambled == word and attempts < 10:
        scrambled = ''.join(random.sample(word, len(word)))
        attempts += 1
    
    return {
        'question': f'Unscramble this word:\n<code>{scrambled}</code>',
        'answer': word,
        'type': 'unscramble'
    }

def generate_simple_question():
    """Generate simple question"""
    random.seed(datetime.now().timestamp() + random.random())
    
    questions = [
        {'question': 'What color is the sky?', 'answer': 'BLUE', 'options': ['RED', 'BLUE', 'GREEN', 'YELLOW']},
        {'question': 'How many days in a week?', 'answer': '7', 'options': ['5', '6', '7', '8']},
        {'question': 'What is 10 ÷ 2?', 'answer': '5', 'options': ['3', '4', '5', '6']},
        {'question': 'Capital of India?', 'answer': 'DELHI', 'options': ['MUMBAI', 'DELHI', 'KOLKATA', 'CHENNAI']},
        {'question': 'How many months in a year?', 'answer': '12', 'options': ['10', '11', '12', '13']},
        {'question': 'Sun rises in the?', 'answer': 'EAST', 'options': ['NORTH', 'SOUTH', 'EAST', 'WEST']},
        {'question': 'How many colors in a rainbow?', 'answer': '7', 'options': ['5', '6', '7', '8']},
        {'question': 'Which is largest?\n🐘 🐁 🐈 🐕', 'answer': '🐘', 'options': ['🐘', '🐁', '🐈', '🐕']},
        {'question': 'What do bees make?', 'answer': 'HONEY', 'options': ['MILK', 'HONEY', 'WATER', 'JUICE']},
        {'question': 'How many sides in a triangle?', 'answer': '3', 'options': ['2', '3', '4', '5']},
        {'question': 'What is 5 × 5?', 'answer': '25', 'options': ['20', '25', '30', '35']},
        {'question': 'Which is hot?', 'answer': '🔥', 'options': ['❄️', '🔥', '💧', '🌊']},
        {'question': 'How many eyes do humans have?', 'answer': '2', 'options': ['1', '2', '3', '4']},
        {'question': 'Which is sweet?', 'answer': '🍯', 'options': ['🧂', '🍯', '🌶️', '🥒']},
        {'question': 'Capital of France?', 'answer': 'PARIS', 'options': ['LONDON', 'PARIS', 'ROME', 'BERLIN']},
        {'question': 'What is 100 ÷ 10?', 'answer': '10', 'options': ['5', '10', '15', '20']},
        {'question': 'How many hours in a day?', 'answer': '24', 'options': ['12', '20', '24', '30']},
        {'question': 'Which planet do we live on?', 'answer': 'EARTH', 'options': ['MARS', 'EARTH', 'VENUS', 'JUPITER']},
    ]
    
    selected = random.choice(questions)
    return {
        'question': selected['question'],
        'answer': selected['answer'],
        'options': selected['options'],
        'type': 'simple'
    }

def generate_random_captcha():
    """Generate random captcha"""
    random.seed(datetime.now().timestamp() + random.random())
    
    captcha_types = ['image', 'math', 'pattern', 'unscramble', 'simple']
    captcha_type = random.choice(captcha_types)
    
    if captcha_type == 'image':
        text = generate_text_captcha()
        return {'type': 'image', 'text': text, 'answer': text}
    elif captcha_type == 'math':
        return generate_math_captcha()
    elif captcha_type == 'pattern':
        return generate_pattern_captcha()
    elif captcha_type == 'unscramble':
        return generate_word_unscramble()
    else:
        return generate_simple_question()

# ==================== UTILITY FUNCTIONS ====================

def reset_daily_captchas():
    """Reset captchas for new day - CRITICAL FUNCTION"""
    data = load_data()
    today = datetime.now().strftime('%Y-%m-%d')
    
    for user_id in data:
        if user_id not in ['pending_rejection', 'bot_stats']:
            # Check if it's a new day
            if data[user_id].get('last_reset') != today:
                # Generate new daily captcha count (3 or 4)
                random.seed(int(user_id) + int(datetime.now().timestamp()))
                new_count = random.randint(3, 4)
                
                # Reset for new day
                data[user_id]['completed_captchas'] = []
                data[user_id]['last_reset'] = today
                data[user_id]['daily_captcha_count'] = new_count
                
                print(f"✅ Reset user {user_id}: {new_count} tasks for {today}")
    
    save_data(data)

def get_available_captchas(user_id):
    """Get available captchas - FIXED COUNT PER DAY"""
    user_data = get_user_data(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Check if reset needed
    if user_data.get('last_reset') != today:
        # Generate count for this user for today (3 or 4)
        random.seed(int(user_id) + int(datetime.now().timestamp()))
        total_captchas = random.randint(3, 4)
        
        # Reset
        update_user_data(user_id, {
            'completed_captchas': [],
            'last_reset': today,
            'daily_captcha_count': total_captchas
        })
        
        user_data = get_user_data(user_id)
    else:
        # Use stored count
        total_captchas = user_data.get('daily_captcha_count', 3)
        if total_captchas == 0:  # Safety check
            total_captchas = random.randint(3, 4)
            update_user_data(user_id, {'daily_captcha_count': total_captchas})
    
    completed = user_data.get('completed_captchas', [])
    available = [i for i in range(1, total_captchas + 1) if i not in completed]
    
    return available, total_captchas

def get_main_menu():
    """Main menu buttons"""
    return [
        [Button.inline('📝 Solve Captcha', b'solve_captcha'), Button.inline('💰 My Balance', b'my_balance')],
        [Button.inline('💸 Withdraw', b'withdraw'), Button.inline('📊 Statistics', b'statistics')],
        [Button.inline('ℹ️ Help', b'help'), Button.inline('📞 Support', b'support')]
    ]

def format_number(num):
    """Format number with commas"""
    return f"{num:,}"

# ==================== BOT HANDLERS ====================

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    """Handle /start command"""
    reset_daily_captchas()
    user = await event.get_sender()
    get_user_data(event.sender_id)
    
    welcome_text = f"""🎊 <b>Welcome {user.first_name}!</b> 🎊

💼 <b>Captcha Solving Bot</b>

Solve captchas daily and earn <b>real money</b>! 💰

╔═══════════════════╗
║  <b>HOW IT WORKS:</b>  ║
╚═══════════════════╝

✅ Solve <code>3-4</code> captchas every 24 hours
💵 Earn <code>₹50</code> per captcha
🎯 Withdraw via <b>UPI or QR Code</b>
⚡ Get paid within <b>24 hours</b>
🔄 New tasks available every day at midnight

💡 <b>NEW:</b> You can now send QR code for faster payments!

👇 <b>Click below to get started!</b> 👇"""
    
    await event.respond(
        welcome_text,
        buttons=get_main_menu(),
        parse_mode='html'
    )

@bot.on(events.NewMessage(pattern='/admin'))
async def admin_panel(event):
    """Admin panel"""
    if event.sender_id != ADMIN_ID:
        return
    
    data = load_data()
    total_users = len([k for k in data.keys() if k not in ['pending_rejection', 'bot_stats']])
    total_balance = sum(data[k].get('balance', 0) for k in data.keys() if k not in ['pending_rejection', 'bot_stats'])
    total_earned = sum(data[k].get('total_earned', 0) for k in data.keys() if k not in ['pending_rejection', 'bot_stats'])
    total_withdrawn = sum(data[k].get('total_withdrawn', 0) for k in data.keys() if k not in ['pending_rejection', 'bot_stats'])
    
    # Active today
    today = datetime.now().strftime('%Y-%m-%d')
    active_today = len([k for k in data.keys() if k not in ['pending_rejection', 'bot_stats'] and data[k].get('last_active', '').startswith(today)])
    
    admin_text = f"""👨‍💼 <b>ADMIN PANEL</b>

╔═══════════════════╗
║  <b>BOT STATISTICS</b> ║
╚═══════════════════╝

👥 Total Users: <b>{format_number(total_users)}</b>
🟢 Active Today: <b>{format_number(active_today)}</b>

💰 Total Balance: <b>₹{format_number(total_balance)}</b>
💵 Total Earned: <b>₹{format_number(total_earned)}</b>
💸 Total Withdrawn: <b>₹{format_number(total_withdrawn)}</b>

⏰ Next Reset: <b>{format_time_left()}</b>

<b>Commands:</b>
/broadcast - Send message to all users
/stats - Detailed statistics
/users - List all users"""
    
    await event.respond(admin_text, parse_mode='html')

@bot.on(events.CallbackQuery(pattern=b'solve_captcha'))
async def solve_captcha_menu(event):
    """Show available captchas"""
    user_id = event.sender_id
    reset_daily_captchas()  # Auto-reset if needed
    
    available, total = get_available_captchas(user_id)
    user_data = get_user_data(user_id)
    completed_count = len(user_data.get('completed_captchas', []))
    
    if not available:
        time_left = format_time_left()
        
        await event.edit(
            f"✅ <b>All Captchas Completed!</b>\n\n"
            f"🎉 <b>Amazing work!</b> You've finished all {total} captchas for today.\n\n"
            f"╔═══════════════════╗\n"
            f"║  <b>NEXT RESET</b>   ║\n"
            f"╚═══════════════════╝\n\n"
            f"⏰ New tasks in: <b>{time_left}</b>\n"
            f"📅 Reset time: <b>12:00 AM (Midnight)</b>\n"
            f"🎯 Tasks tomorrow: <b>3-4</b> captchas\n\n"
            f"💰 Check your balance and withdraw!\n\n"
            f"<i>See you tomorrow for more earnings!</i> 🚀",
            buttons=[
                [Button.inline('💰 My Balance', b'my_balance')], 
                [Button.inline('💸 Withdraw', b'withdraw')],
                [Button.inline('🔙 Main Menu', b'back_to_menu')]
            ],
            parse_mode='html'
        )
        return
    
    progress_bar = '█' * completed_count + '░' * (total - completed_count)
    time_left = format_time_left()
    
    text = f"""📝 <b>Available Captcha Tasks</b>

╔═══════════════════╗
║   <b>PROGRESS</b>    ║
╚═══════════════════╝

{progress_bar}

✅ <b>Completed:</b> <code>{completed_count}/{total}</code>
💵 <b>Reward:</b> <code>₹50</code> per captcha
🎯 <b>Remaining:</b> <code>{len(available)}</code> tasks
💰 <b>Potential Earnings:</b> ₹{len(available) * 50}

⏰ <b>Tasks Reset in:</b> {time_left}
🔄 <b>Reset Time:</b> 12:00 AM Daily

<b>Select a task below:</b> 👇"""
    
    buttons = []
    for task_num in range(1, total + 1):
        if task_num in available:
            buttons.append([Button.inline(f'✨ Task {task_num} - Solve Now (₹50)', f'task_{task_num}'.encode())])
        else:
            buttons.append([Button.inline(f'✔️ Task {task_num} - Completed ✓', f'completed_{task_num}'.encode())])
    
    buttons.append([Button.inline('🔙 Back to Menu', b'back_to_menu')])
    
    await event.edit(text, buttons=buttons, parse_mode='html')

@bot.on(events.CallbackQuery(pattern=b'task_'))
async def handle_task(event):
    """Generate and send captcha"""
    user_id = event.sender_id
    task_num = int(event.data.decode().split('_')[1])
    
    user_data = get_user_data(user_id)
    if task_num in user_data.get('completed_captchas', []):
        await event.answer('❌ Already completed!', alert=True)
        return
    
    captcha_data = generate_random_captcha()
    captcha_type = captcha_data['type']
    
    captchas = load_captchas()
    captchas[str(user_id)] = {
        'answer': captcha_data['answer'].upper(),
        'task_num': task_num,
        'type': captcha_type
    }
    save_captchas(captchas)
    
    await event.delete()
    
    if captcha_type == 'image':
        captcha_image = create_captcha_image(captcha_data['text'])
        
        caption_text = f"""🔐 <b>Task {task_num} - Image Captcha</b>

╔═══════════════════╗
║  <b>INSTRUCTIONS</b> ║
╚═══════════════════╝

📝 Type the text shown in the image
💰 Reward: <b>₹50</b>
⚠️ Case doesn't matter
⏱️ No time limit

<b>Reply with the captcha text:</b> 👇"""
        
        await bot.send_message(
            event.chat_id,
            file=captcha_image,
            message=caption_text,
            buttons=[[Button.inline('🔙 Cancel', b'solve_captcha')]],
            parse_mode='html'
        )
    
    elif captcha_type == 'math':
        await bot.send_message(
            event.chat_id,
            f"🔐 <b>Task {task_num} - Math Challenge</b>\n\n"
            f"╔═══════════════════╗\n"
            f"║  <b>SOLVE THIS</b>  ║\n"
            f"╚═══════════════════╝\n\n"
            f"🧮 <b>Question:</b>\n"
            f"<code>{captcha_data['question']} = ?</code>\n\n"
            f"💰 Reward: <b>₹50</b>\n"
            f"⚠️ Enter only the answer (number)\n"
            f"⏱️ No time limit\n\n"
            f"<b>Reply with your answer:</b> 👇",
            buttons=[[Button.inline('🔙 Cancel', b'solve_captcha')]],
            parse_mode='html'
        )
    
    elif captcha_type == 'pattern':
        options_text = '\n'.join([f"  {i+1}. {opt}" for i, opt in enumerate(captcha_data['options'])])
        
        await bot.send_message(
            event.chat_id,
            f"🔐 <b>Task {task_num} - Pattern Challenge</b>\n\n"
            f"╔═══════════════════╗\n"
            f"║  <b>FIND THE ANSWER</b>  ║\n"
            f"╚═══════════════════╝\n\n"
            f"❓ <b>Question:</b>\n"
            f"{captcha_data['question']}\n\n"
            f"📋 <b>Options:</b>\n"
            f"{options_text}\n\n"
            f"💰 Reward: <b>₹50</b>\n"
            f"💡 Reply with the answer or number\n\n"
            f"<b>Reply with your answer:</b> 👇",
            buttons=[[Button.inline('🔙 Cancel', b'solve_captcha')]],
            parse_mode='html'
        )
    
    elif captcha_type == 'unscramble':
        await bot.send_message(
            event.chat_id,
            f"🔐 <b>Task {task_num} - Word Puzzle</b>\n\n"
            f"╔═══════════════════╗\n"
            f"║  <b>UNSCRAMBLE</b>  ║\n"
            f"╚═══════════════════╝\n\n"
            f"🔤 {captcha_data['question']}\n\n"
            f"💡 <b>Hint:</b> It's a common English word\n"
            f"💰 Reward: <b>₹50</b>\n"
            f"⚠️ Case doesn't matter\n\n"
            f"<b>Reply with the correct word:</b> 👇",
            buttons=[[Button.inline('🔙 Cancel', b'solve_captcha')]],
            parse_mode='html'
        )
    
    else:
        options_text = '\n'.join([f"  {i+1}. {opt}" for i, opt in enumerate(captcha_data['options'])])
        
        await bot.send_message(
            event.chat_id,
            f"🔐 <b>Task {task_num} - Quick Question</b>\n\n"
            f"╔═══════════════════╗\n"
            f"║  <b>ANSWER THIS</b>  ║\n"
            f"╚═══════════════════╝\n\n"
            f"❓ <b>Question:</b>\n"
            f"{captcha_data['question']}\n\n"
            f"📋 <b>Options:</b>\n"
            f"{options_text}\n\n"
            f"💰 Reward: <b>₹50</b>\n"
            f"💡 Reply with the answer or number\n\n"
            f"<b>Reply with your answer:</b> 👇",
            buttons=[[Button.inline('🔙 Cancel', b'solve_captcha')]],
            parse_mode='html'
        )

@bot.on(events.NewMessage(func=lambda e: e.is_private and not e.message.message.startswith('/') and not e.message.photo))
async def handle_text_input(event):
    """Handle text inputs (captcha answers/UPI)"""
    user_id = event.sender_id
    user_input = event.message.message.strip()
    
    # Admin rejection remark
    if user_id == ADMIN_ID:
        data = load_data()
        if 'pending_rejection' in data:
            rejection = data['pending_rejection']
            target_user = rejection['user_id']
            withdrawal_id = rejection['withdrawal_id']
            amount = rejection.get('amount', 0)
            
            # Ensure user exists in data before updating
            target_user_str = str(target_user)
            if target_user_str not in data:
                # Recreate user data if missing
                get_user_data(target_user)
                data = load_data()
            
            # Return money
            data[target_user_str]['balance'] += amount
            save_data(data)
            
            try:
                await bot.send_message(
                    target_user,
                    f"❌ <b>Payment Rejected</b>\n\n"
                    f"📝 Transaction ID: <code>{withdrawal_id}</code>\n"
                    f"💰 Amount Refunded: <b>₹{amount}</b>\n\n"
                    f"📋 <b>Reason:</b>\n"
                    f"<i>{user_input}</i>\n\n"
                    f"💡 Your balance has been restored.\n"
                    f"Please check your UPI/QR and try again.",
                    buttons=get_main_menu(),
                    parse_mode='html'
                )
                
                await event.respond("✅ <b>Rejection sent successfully!</b>", parse_mode='html')
            except Exception as e:
                await event.respond(f"❌ Error: {str(e)}")
            
            del data['pending_rejection']
            save_data(data)
            return
    
    # Check user state
    user_state = user_states.get(user_id, {}).get('state')
    
    # Handle UPI input
    if user_state == 'waiting_upi':
        upi_id = user_input
        
        # Validate UPI
        if '@' not in upi_id or len(upi_id) < 5:
            await event.respond(
                "❌ <b>Invalid UPI ID!</b>\n\n"
                "Please enter a valid UPI ID\n"
                "Example: <code>yourname@paytm</code>\n\n"
                "Or click below to send QR code instead:",
                buttons=[
                    [Button.inline('📸 Send QR Code Instead', b'send_qr')],
                    [Button.inline('🔙 Back', b'back_to_menu')]
                ],
                parse_mode='html'
            )
            return
        
        # Store UPI and ask for confirmation
        user_states[user_id] = {
            'state': 'confirm_withdrawal',
            'upi_id': upi_id,
            'qr_code': None
        }
        
        user_data = get_user_data(user_id)
        balance = user_data['balance']
        
        await event.respond(
            f"📋 <b>Confirm Withdrawal Details</b>\n\n"
            f"╔═══════════════════╗\n"
            f"║  <b>PAYMENT INFO</b> ║\n"
            f"╚═══════════════════╝\n\n"
            f"💰 Amount: <b>₹{balance}</b>\n"
            f"🆔 UPI ID: <code>{upi_id}</code>\n"
            f"📸 QR Code: <i>Not provided</i>\n\n"
            f"⚠️ <b>Please verify your UPI ID is correct!</b>\n\n"
            f"You can also send a QR code for faster payment:",
            buttons=[
                [Button.inline('✅ Confirm & Submit', b'confirm_withdrawal')],
                [Button.inline('📸 Add QR Code', b'send_qr')],
                [Button.inline('🔙 Cancel', b'back_to_menu')]
            ],
            parse_mode='html'
        )
        return
    
    # Handle captcha answer
    captchas = load_captchas()
    user_id_str = str(user_id)
    
    if user_id_str in captchas:
        captcha_data = captchas[user_id_str]
        user_answer = user_input.upper().strip()
        correct_answer = captcha_data['answer'].upper().strip()
        task_num = captcha_data['task_num']
        
        data = load_data()
        
        if user_answer == correct_answer:
            if task_num not in data[user_id_str].get('completed_captchas', []):
                data[user_id_str]['balance'] += 50
                data[user_id_str]['completed_captchas'].append(task_num)
                data[user_id_str]['total_earned'] += 50
                save_data(data)
                
                del captchas[user_id_str]
                save_captchas(captchas)
                
                # Check remaining
                available, total = get_available_captchas(user_id)
                
                if available:
                    remaining_text = f"\n🎯 <b>Remaining tasks:</b> {len(available)}\n💰 <b>Potential:</b> ₹{len(available) * 50}"
                else:
                    time_left = format_time_left()
                    remaining_text = f"\n🎉 <b>All tasks completed!</b>\n⏰ <b>Next reset:</b> {time_left}"
                
                await event.respond(
                    f"✅ <b>CORRECT ANSWER!</b>\n\n"
                    f"🎉 <b>Congratulations!</b>\n"
                    f"✨ Task {task_num} completed successfully!\n\n"
                    f"💰 <b>+₹50</b> added to your account\n"
                    f"💵 <b>Current Balance:</b> ₹{data[user_id_str]['balance']}\n"
                    f"{remaining_text}\n\n"
                    f"<i>Keep solving to earn more!</i> 🚀",
                    buttons=[
                        [Button.inline('📝 Solve More', b'solve_captcha'), Button.inline('💰 Balance', b'my_balance')],
                        [Button.inline('🔙 Main Menu', b'back_to_menu')]
                    ],
                    parse_mode='html'
                )
            else:
                await event.respond(
                    "⚠️ <b>Already completed this task!</b>",
                    buttons=get_main_menu(),
                    parse_mode='html'
                )
        else:
            # Wrong answer - increment failed attempts
            data[user_id_str]['failed_attempts'] = data[user_id_str].get('failed_attempts', 0) + 1
            save_data(data)
            
            del captchas[user_id_str]
            save_captchas(captchas)
            
            await event.respond(
                f"❌ <b>WRONG ANSWER!</b>\n\n"
                f"😔 Incorrect answer entered.\n\n"
                f"Your answer: <code>{user_answer}</code>\n"
                f"Correct answer: <code>{correct_answer}</code>\n\n"
                f"💡 <b>Tip:</b> Read carefully and try again!\n"
                f"⚠️ No penalty - you can retry!",
                buttons=[
                    [Button.inline('🔄 Try Another Task', b'solve_captcha')],
                    [Button.inline('🔙 Main Menu', b'back_to_menu')]
                ],
                parse_mode='html'
            )

@bot.on(events.NewMessage(func=lambda e: e.is_private and e.message.photo))
async def handle_photo(event):
    """Handle QR code upload"""
    user_id = event.sender_id
    user_state = user_states.get(user_id, {}).get('state')
    
    if user_state in ['waiting_qr', 'waiting_upi', 'confirm_withdrawal']:
        # Download QR code
        photo = await event.download_media(file=bytes)
        
        # Save QR code
        qr_filename = f"qr_{user_id}_{int(datetime.now().timestamp())}.jpg"
        qr_path = QR_DIR / qr_filename
        
        with open(qr_path, 'wb') as f:
            f.write(photo)
        
        # Update state
        current_upi = user_states.get(user_id, {}).get('upi_id', '')
        user_states[user_id] = {
            'state': 'confirm_withdrawal',
            'upi_id': current_upi,
            'qr_code': str(qr_path)
        }
        
        user_data = get_user_data(user_id)
        balance = user_data['balance']
        
        if balance < 50:
            await event.respond(
                "❌ Insufficient balance!",
                buttons=get_main_menu(),
                parse_mode='html'
            )
            return
        
        upi_text = f"🆔 UPI ID: <code>{current_upi}</code>" if current_upi else "🆔 UPI ID: <i>Not provided</i>"
        
        await event.respond(
            f"✅ <b>QR Code Received!</b>\n\n"
            f"📋 <b>Confirm Withdrawal Details</b>\n\n"
            f"╔═══════════════════╗\n"
            f"║  <b>PAYMENT INFO</b> ║\n"
            f"╚═══════════════════╝\n\n"
            f"💰 Amount: <b>₹{balance}</b>\n"
            f"{upi_text}\n"
            f"📸 QR Code: <b>✅ Uploaded</b>\n\n"
            f"⚠️ <b>Please verify all details!</b>\n\n"
            f"Click confirm to submit your withdrawal request:",
            buttons=[
                [Button.inline('✅ Confirm & Submit', b'confirm_withdrawal')],
                [Button.inline('✏️ Enter UPI ID', b'enter_upi')],
                [Button.inline('🔙 Cancel', b'back_to_menu')]
            ],
            parse_mode='html'
        )
    else:
        await event.respond(
            "⚠️ Please start withdrawal process first.",
            buttons=get_main_menu(),
            parse_mode='html'
        )

@bot.on(events.CallbackQuery(pattern=b'send_qr'))
async def send_qr_prompt(event):
    """Prompt user to send QR code"""
    user_id = event.sender_id
    user_states[user_id] = {'state': 'waiting_qr'}
    
    await event.edit(
        f"📸 <b>Send Your QR Code</b>\n\n"
        f"╔═══════════════════╗\n"
        f"║  <b>INSTRUCTIONS</b> ║\n"
        f"╚═══════════════════╝\n\n"
        f"1️⃣ Open your payment app (PayTM, PhonePe, GPay, etc.)\n"
        f"2️⃣ Go to your QR code section\n"
        f"3️⃣ Take a screenshot or save the QR code\n"
        f"4️⃣ Send the image here\n\n"
        f"💡 <b>Tip:</b> QR code makes payment faster!\n\n"
        f"📤 <b>Send your QR code image now:</b>",
        buttons=[
            [Button.inline('✏️ Enter UPI ID Instead', b'enter_upi')],
            [Button.inline('🔙 Cancel', b'back_to_menu')]
        ],
        parse_mode='html'
    )

@bot.on(events.CallbackQuery(pattern=b'enter_upi'))
async def enter_upi_prompt(event):
    """Prompt user to enter UPI"""
    user_id = event.sender_id
    user_states[user_id] = {'state': 'waiting_upi'}
    
    await event.edit(
        f"💸 <b>Enter Your UPI ID</b>\n\n"
        f"╔═══════════════════╗\n"
        f"║  <b>INSTRUCTIONS</b> ║\n"
        f"╚═══════════════════╝\n\n"
        f"📝 <b>Enter your UPI ID:</b>\n"
        f"<i>Example: yourname@paytm, 9876543210@paytm</i>\n\n"
        f"⚠️ <b>Important:</b> Double-check your UPI ID!\n\n"
        f"You can also send QR code for faster payment:",
        buttons=[
            [Button.inline('📸 Send QR Code Instead', b'send_qr')],
            [Button.inline('🔙 Cancel', b'back_to_menu')]
        ],
        parse_mode='html'
    )

@bot.on(events.CallbackQuery(pattern=b'confirm_withdrawal'))
async def confirm_withdrawal(event):
    """Confirm and process withdrawal"""
    user_id = event.sender_id
    user_state = user_states.get(user_id, {})
    
    upi_id = user_state.get('upi_id', '')
    qr_code = user_state.get('qr_code')
    
    if not upi_id and not qr_code:
        await event.answer('⚠️ Please provide UPI ID or QR code!', alert=True)
        return
    
    user_data = get_user_data(user_id)
    balance = user_data['balance']
    
    if balance < 50:
        await event.answer('❌ Insufficient balance!', alert=True)
        return
    
    withdrawal_id = f"W{user_id}{int(datetime.now().timestamp())}"
    
    # Deduct balance
    update_user_data(user_id, {'balance': 0})
    
    # Clear state
    if user_id in user_states:
        del user_states[user_id]
    
    # Confirm to user
    upi_text = f"🆔 UPI ID: <code>{upi_id}</code>\n" if upi_id else ""
    qr_text = "📸 QR Code: <b>✅ Provided</b>\n" if qr_code else ""
    
    await event.edit(
        f"✅ <b>Withdrawal Request Submitted!</b>\n\n"
        f"╔═══════════════════╗\n"
        f"║  <b>PAYMENT INFO</b> ║\n"
        f"╚═══════════════════╝\n\n"
        f"💰 Amount: <b>₹{balance}</b>\n"
        f"{upi_text}"
        f"{qr_text}"
        f"📝 Transaction ID: <code>{withdrawal_id}</code>\n"
        f"⏰ Processing Time: <b>24 hours</b>\n\n"
        f"<i>You'll be notified once processed!</i> 🔔\n\n"
        f"Thank you! 🙏",
        buttons=get_main_menu(),
        parse_mode='html'
    )
    
    # Notify admin with clickable profile link
    admin_text = (
        f"🔔 <b>NEW WITHDRAWAL REQUEST</b>\n\n"
        f"╔═══════════════════╗\n"
        f"║  <b>USER DETAILS</b> ║\n"
        f"╚═══════════════════╝\n\n"
        f"👤 User ID: <code>{user_id}</code>\n"
        f"👤 Profile: <a href='tg://user?id={user_id}'>CLICK TO CHECK PROFILE</a>\n"
        f"💰 Amount: <b>₹{balance}</b>\n"
    )
    
    if upi_id:
        admin_text += f"🆔 UPI ID: <code>{upi_id}</code>\n"
    
    admin_text += (
        f"📝 Transaction ID: <code>{withdrawal_id}</code>\n"
        f"🕐 Time: <code>{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</code>\n\n"
        f"<b>Action Required:</b>"
    )
    
    buttons = [
        [Button.inline('✅ Approve Payment', f'approve_{user_id}_{withdrawal_id}_{balance}'.encode())],
        [Button.inline('❌ Reject Payment', f'reject_{user_id}_{withdrawal_id}_{balance}'.encode())]
    ]
    
    # Send to admin
    if qr_code and os.path.exists(qr_code):
        await bot.send_message(
            ADMIN_ID,
            file=qr_code,
            message=admin_text,
            buttons=buttons,
            parse_mode='html'
        )
    else:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            buttons=buttons,
            parse_mode='html'
        )

@bot.on(events.CallbackQuery(pattern=b'my_balance'))
async def show_balance(event):
    """Show user balance"""
    user_id = event.sender_id
    user_data = get_user_data(user_id)
    
    balance = user_data.get('balance', 0)
    total_earned = user_data.get('total_earned', 0)
    total_withdrawn = user_data.get('total_withdrawn', 0)
    completed_today = len(user_data.get('completed_captchas', []))
    
    available, total = get_available_captchas(user_id)
    potential = len(available) * 50
    
    time_left = format_time_left()
    
    tip_text = "💡 <i>Solve captchas to increase balance!</i>" if balance < 50 else "🎉 <i>You can withdraw now!</i>"
    
    await event.edit(
        f"💰 <b>YOUR ACCOUNT</b>\n\n"
        f"╔═══════════════════╗\n"
        f"║   <b>STATISTICS</b>  ║\n"
        f"╚═══════════════════╝\n\n"
        f"👤 <b>User ID:</b> <code>{user_id}</code>\n\n"
        f"💵 <b>Current Balance:</b> ₹{balance}\n"
        f"📊 <b>Total Earned:</b> ₹{total_earned}\n"
        f"💸 <b>Total Withdrawn:</b> ₹{total_withdrawn}\n"
        f"✅ <b>Today's Tasks:</b> {completed_today}/{total}\n"
        f"🎯 <b>Potential Today:</b> ₹{potential}\n\n"
        f"⏰ <b>Next Reset:</b> {time_left}\n\n"
        f"{tip_text}",
        buttons=[
            [Button.inline('💸 Withdraw', b'withdraw'), Button.inline('📊 Statistics', b'statistics')],
            [Button.inline('🔙 Back to Menu', b'back_to_menu')]
        ],
        parse_mode='html'
    )

@bot.on(events.CallbackQuery(pattern=b'withdraw'))
async def withdraw_menu(event):
    """Withdrawal menu"""
    user_id = event.sender_id
    user_data = get_user_data(user_id)
    balance = user_data.get('balance', 0)
    
    if balance < 50:
        needed = 50 - balance
        captchas_needed = (needed + 49) // 50
        
        available, total = get_available_captchas(user_id)
        time_left = format_time_left()
        
        if len(available) >= captchas_needed:
            when_text = f"💡 Solve <b>{captchas_needed}</b> more captcha(s) today to withdraw!"
        else:
            when_text = f"⏰ Complete today's tasks and earn more tomorrow!\n🔄 Reset in: {time_left}"
        
        await event.edit(
            f"❌ <b>Insufficient Balance</b>\n\n"
            f"💵 <b>Your Balance:</b> ₹{balance}\n"
            f"⚠️ <b>Minimum Required:</b> ₹50\n"
            f"📉 <b>You Need:</b> ₹{needed} more\n\n"
            f"{when_text}\n\n"
            f"<i>Keep earning!</i> 💪",
            buttons=[
                [Button.inline('📝 Solve Captcha', b'solve_captcha')],
                [Button.inline('🔙 Back', b'back_to_menu')]
            ],
            parse_mode='html'
        )
        return
    
    # Set state
    user_states[user_id] = {'state': 'choosing_method'}
    
    await event.edit(
        f"💸 <b>WITHDRAW FUNDS</b>\n\n"
        f"╔═══════════════════╗\n"
        f"║  <b>YOUR BALANCE</b> ║\n"
        f"╚═══════════════════╝\n\n"
        f"💰 Available: <b>₹{balance}</b>\n\n"
        f"<b>Choose withdrawal method:</b>\n\n"
        f"1️⃣ <b>UPI ID</b> - Enter your UPI ID\n"
        f"2️⃣ <b>QR Code</b> - Upload payment QR code (Faster!)\n"
        f"3️⃣ <b>Both</b> - Provide both for best results\n\n"
        f"⚠️ <b>Important:</b> Ensure details are correct!",
        buttons=[
            [Button.inline('🆔 Enter UPI ID', b'enter_upi')],
            [Button.inline('📸 Send QR Code', b'send_qr')],
            [Button.inline('🔙 Cancel', b'back_to_menu')]
        ],
        parse_mode='html'
    )

@bot.on(events.CallbackQuery(pattern=b'statistics'))
async def show_statistics(event):
    """Show user statistics"""
    user_id = event.sender_id
    user_data = get_user_data(user_id)
    
    balance = user_data.get('balance', 0)
    total_earned = user_data.get('total_earned', 0)
    total_withdrawn = user_data.get('total_withdrawn', 0)
    successful_withdrawals = user_data.get('successful_withdrawals', 0)
    failed_attempts = user_data.get('failed_attempts', 0)
    joined_date = user_data.get('joined_date', 'N/A')
    
    completed_today = len(user_data.get('completed_captchas', []))
    available, total = get_available_captchas(user_id)
    
    success_rate = 0
    if completed_today + failed_attempts > 0:
        success_rate = (completed_today / (completed_today + failed_attempts)) * 100
    
    time_left = format_time_left()
    
    await event.edit(
        f"📊 <b>YOUR STATISTICS</b>\n\n"
        f"╔═══════════════════╗\n"
        f"║  <b>ACCOUNT INFO</b>  ║\n"
        f"╚═══════════════════╝\n\n"
        f"👤 User ID: <code>{user_id}</code>\n"
        f"📅 Member Since: <code>{joined_date}</code>\n\n"
        f"╔═══════════════════╗\n"
        f"║   <b>EARNINGS</b>    ║\n"
        f"╚═══════════════════╝\n\n"
        f"💰 Current Balance: <b>₹{balance}</b>\n"
        f"📈 Total Earned: <b>₹{total_earned}</b>\n"
        f"💸 Total Withdrawn: <b>₹{total_withdrawn}</b>\n"
        f"✅ Successful Withdrawals: <b>{successful_withdrawals}</b>\n\n"
        f"╔═══════════════════╗\n"
        f"║  <b>TODAY'S TASKS</b> ║\n"
        f"╚═══════════════════╝\n\n"
        f"✅ Completed: <b>{completed_today}/{total}</b>\n"
        f"🎯 Remaining: <b>{len(available)}</b>\n"
        f"❌ Failed Attempts: <b>{failed_attempts}</b>\n"
        f"📊 Success Rate: <b>{success_rate:.1f}%</b>\n\n"
        f"⏰ <b>Next Reset:</b> {time_left}\n"
        f"🔄 <b>Reset Time:</b> 12:00 AM Daily\n\n"
        f"<i>Keep up the great work!</i> 🚀",
        buttons=[
            [Button.inline('💰 My Balance', b'my_balance')],
            [Button.inline('🔙 Back to Menu', b'back_to_menu')]
        ],
        parse_mode='html'
    )

@bot.on(events.CallbackQuery(pattern=b'help'))
async def show_help(event):
    """Show help"""
    time_left = format_time_left()
    
    await event.edit(
        "ℹ️ <b>HELP &amp; INFORMATION</b>\n\n"
        "╔═══════════════════╗\n"
        "║  <b>HOW IT WORKS</b>  ║\n"
        "╚═══════════════════╝\n\n"
        "<b>Step-by-Step Guide:</b>\n\n"
        "1️⃣ Click <b>\"📝 Solve Captcha\"</b>\n"
        "2️⃣ Select an available task\n"
        "3️⃣ Solve the challenge carefully\n"
        "4️⃣ Enter your answer\n"
        "5️⃣ Earn <b>₹50</b> for correct answers\n"
        "6️⃣ Check balance anytime\n"
        "7️⃣ Withdraw when you have ₹50+\n\n"
        "╔═══════════════════╗\n"
        "║ <b>CAPTCHA TYPES</b> ║\n"
        "╚═══════════════════╝\n\n"
        "🖼️ <b>Image:</b> Type the text from image\n"
        "🧮 <b>Math:</b> Solve calculations\n"
        "🧩 <b>Pattern:</b> Find the correct answer\n"
        "🔤 <b>Word Puzzle:</b> Unscramble words\n"
        "❓ <b>Questions:</b> General knowledge\n\n"
        "╔═══════════════════╗\n"
        "║ <b>TASK SCHEDULE</b> ║\n"
        "╚═══════════════════╝\n\n"
        "📅 <b>Daily Tasks:</b> 3-4 captchas\n"
        "🕛 <b>Reset Time:</b> 12:00 AM (Midnight)\n"
        f"⏰ <b>Next Reset:</b> {time_left}\n"
        "🔄 <b>Frequency:</b> Every 24 hours\n"
        "💰 <b>Earnings:</b> ₹150-200 per day\n\n"
        "╔═══════════════════╗\n"
        "║ <b>WITHDRAWAL</b>   ║\n"
        "╚═══════════════════╝\n\n"
        "💵 Minimum: <b>₹50</b>\n"
        "🆔 <b>Option 1:</b> UPI ID\n"
        "📸 <b>Option 2:</b> QR Code (Faster!)\n"
        "⚡ Payment: <b>Within 24 hours</b>\n"
        "✅ Both methods accepted\n\n"
        "╔═══════════════════╗\n"
        "║ <b>IMPORTANT INFO</b>║\n"
        "╚═══════════════════╝\n\n"
        "⏱️ <b>No time limit</b> per captcha\n"
        "❌ Wrong answers: <b>No penalty</b>\n"
        "🔄 Can retry different tasks\n"
        "🎯 Practice improves accuracy\n"
        "📊 Track your statistics\n\n"
        "<b>Happy Earning!</b> 💰🎉",
        buttons=[
            [Button.inline('📞 Support', b'support')],
            [Button.inline('🔙 Back to Menu', b'back_to_menu')]
        ],
        parse_mode='html'
    )

@bot.on(events.CallbackQuery(pattern=b'support'))
async def show_support(event):
    """Show support info"""
    await event.edit(
        "📞 <b>SUPPORT &amp; CONTACT</b>\n\n"
        "╔═══════════════════╗\n"
        "║   <b>GET HELP</b>    ║\n"
        "╚═══════════════════╝\n\n"
        "Need assistance? We're here to help!\n\n"
        "📧 <b>Contact Methods:</b>\n\n"
        "💬 Telegram: @YourSupport\n"
        "📮 Email: support@example.com\n"
        "🌐 Website: www.example.com\n\n"
        "╔═══════════════════╗\n"
        "║ <b>COMMON ISSUES</b> ║\n"
        "╚═══════════════════╝\n\n"
        "❓ <b>Payment not received?</b>\n"
        "   → Wait 24 hours, then contact\n\n"
        "❓ <b>Wrong UPI/QR submitted?</b>\n"
        "   → Contact immediately\n\n"
        "❓ <b>Captcha not loading?</b>\n"
        "   → Restart bot with /start\n\n"
        "❓ <b>Tasks not resetting?</b>\n"
        "   → Resets at 12:00 AM daily\n\n"
        "❓ <b>Balance not updated?</b>\n"
        "   → Check if answer was correct\n\n"
        "⏰ <b>Support Hours:</b> 24/7\n"
        "⚡ <b>Response Time:</b> 1-6 hours\n\n"
        "<i>We're always happy to help!</i> 😊",
        buttons=[[Button.inline('🔙 Back', b'help')]],
        parse_mode='html'
    )

@bot.on(events.CallbackQuery(pattern=b'approve_'))
async def approve_payment(event):
    """Admin approves payment"""
    if event.sender_id != ADMIN_ID:
        await event.answer('⛔ Unauthorized!', alert=True)
        return
    
    parts = event.data.decode().split('_')
    user_id = int(parts[1])
    withdrawal_id = parts[2]
    amount = int(parts[3])
    
    # Update user data
    data = load_data()
    if str(user_id) in data:
        data[str(user_id)]['total_withdrawn'] = data[str(user_id)].get('total_withdrawn', 0) + amount
        data[str(user_id)]['successful_withdrawals'] = data[str(user_id)].get('successful_withdrawals', 0) + 1
        save_data(data)
    
    try:
        await bot.send_message(
            user_id,
            f"✅ <b>PAYMENT SUCCESSFUL!</b>\n\n"
            f"🎊 <b>Congratulations!</b>\n"
            f"Your payment has been processed!\n\n"
            f"╔═══════════════════╗\n"
            f"║ <b>PAYMENT INFO</b>  ║\n"
            f"╚═══════════════════╝\n\n"
            f"💰 Amount: <b>₹{amount}</b>\n"
            f"📝 Transaction ID: <code>{withdrawal_id}</code>\n"
            f"✅ Status: <b>Completed</b>\n"
            f"📅 Date: <code>{datetime.now().strftime('%d-%m-%Y %H:%M')}</code>\n\n"
            f"💚 Thank you for using our service!\n"
            f"🚀 Keep solving and earning daily!",
            buttons=get_main_menu(),
            parse_mode='html'
        )
        
        try:
            original_text = event.original_update.message.message
        except:
            original_text = "Payment Request"
        
        await event.edit(
            original_text + f"\n\n✅ <b>APPROVED</b>\n⏰ {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
            buttons=None,
            parse_mode='html'
        )
        await event.answer('✅ Payment approved and sent!', alert=True)
    except Exception as e:
        await event.answer(f'❌ Error: {str(e)}', alert=True)

@bot.on(events.CallbackQuery(pattern=b'reject_'))
async def reject_payment(event):
    """Admin rejects payment"""
    if event.sender_id != ADMIN_ID:
        await event.answer('⛔ Unauthorized!', alert=True)
        return
    
    parts = event.data.decode().split('_')
    user_id = int(parts[1])
    withdrawal_id = parts[2]
    amount = int(parts[3])
    
    try:
        original_text = event.original_update.message.message
    except:
        original_text = "Payment Request"
    
    await event.edit(
        original_text + f"\n\n⏳ <b>Waiting for rejection reason...</b>\n"
        f"📝 Please type the reason below:",
        buttons=None,
        parse_mode='html'
    )
    
    data = load_data()
    data['pending_rejection'] = {
        'user_id': user_id,
        'withdrawal_id': withdrawal_id,
        'amount': amount
    }
    save_data(data)

@bot.on(events.CallbackQuery(pattern=b'back_to_menu'))
async def back_to_menu(event):
    """Return to main menu"""
    user = await event.get_sender()
    
    # Clear user state
    user_id = event.sender_id
    if user_id in user_states:
        del user_states[user_id]
    
    await event.edit(
        f"🎊 <b>Welcome Back {user.first_name}!</b>\n\n"
        f"💼 <b>Captcha Solving Bot</b>\n\n"
        f"Solve captchas and earn <b>real money</b>! 💰\n\n"
        f"Select an option below: 👇",
        buttons=get_main_menu(),
        parse_mode='html'
    )

@bot.on(events.CallbackQuery(pattern=b'completed_'))
async def completed_task(event):
    """Handle completed task click"""
    await event.answer('✅ This task is already completed!', alert=True)

# ==================== BACKGROUND TASKS ====================

async def auto_reset_checker():
    """Background task to check and reset daily captchas"""
    while True:
        try:
            reset_daily_captchas()
            print(f"✅ Auto-reset check completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"❌ Error in auto-reset: {e}")
        
        # Check every 10 minutes
        await asyncio.sleep(600)

# ==================== RUN BOT ====================

async def main():
    """Main function to run bot and background tasks"""
    # Start auto-reset checker in background
    asyncio.create_task(auto_reset_checker())
    
    # Run bot
    await bot.run_until_disconnected()

print("=" * 60)
print("🤖 CAPTCHA SOLVING BOT - 24-HOUR RESET VERSION")
print("=" * 60)
print(f"📱 Bot Status: RUNNING")
print(f"👨‍💼 Admin ID: {ADMIN_ID}")
print(f"📁 Data Directory: {DATA_DIR}")
print("=" * 60)
print("\n⏰ TASK SCHEDULE:")
print(f"  📅 Daily Tasks: 3-4 captchas per user")
print(f"  🕛 Reset Time: 12:00 AM (Midnight) daily")
print(f"  🔄 Auto-check: Every 10 minutes")
print(f"  ⏳ Next reset: {format_time_left()}")
print("=" * 60)
print("\n📋 FEATURES:")
print("  ✅ 5 types of random captchas")
print("  ✅ UPI ID support")
print("  ✅ QR Code upload support")
print("  ✅ Fixed 3-4 tasks per 24 hours")
print("  ✅ Automatic midnight reset")
print("  ✅ Detailed statistics")
print("  ✅ Enhanced admin panel")
print("  ✅ Clickable profile link for admin")
print("=" * 60)
print("\n💡 WITHDRAWAL OPTIONS:")
print("  1️⃣  UPI ID only")
print("  2️⃣  QR Code only")
print("  3️⃣  Both UPI ID + QR Code (recommended)")
print("=" * 60)
print("\n🚀 Bot is ready! Tasks reset at midnight daily.")
print("=" * 60)

# Run the bot with background tasks
bot.loop.run_until_complete(main())
