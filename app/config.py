# Day 1: Activity library and routing configuration for Mama Bloom ADK 2.0 agent

# Distress keywords to identify safety/crisis situations
DISTRESS_KEYWORDS = [
    "can't do this",
    "cant do this",
    "want to disappear",
    "want to die",
    "hopeless",
    "no point",
    "end it",
    "ending it",
    "hurt myself",
    "don't want to be here",
    "dont want to be here",
    "give up",
    "can't go on",
    "cant go on",
    "not worth it",
    "better off without me",
    "nobody would care",
    "no one would care",
]

# Standardized crisis message to present when distress is detected
# Contains iCall and Vandrevala Foundation helplines
CRISIS_MESSAGE = (
    "We see you, and you are not alone. What you are feeling is real, and support is available right now. "
    "Please reach out: iCall (India): 9152987821, Vandrevala Foundation: 1860-2662-345 (available 24/7). "
    "You and your baby matter. Please talk to someone today. If you are in immediate danger, "
    "please call emergency services or go to your nearest hospital."
)

# Morning affirmations — MBCP-grounded + Garbha Sanskar framing (20 items)
# Selected randomly each session so they never mechanically repeat.
MORNING_AFFIRMATIONS = [
    # MBCP self-compassion core
    "I am doing something remarkable. It is okay that it is hard.",
    "My body is strong, and I am doing enough every single day.",
    "It is okay to rest; I am nurturing a new life and myself.",
    "I breathe in calm, and I breathe out tension.",
    "I accept myself exactly as I am in this moment.",
    "I am learning and growing along with my baby.",
    "I am allowed to feel all my feelings without judgment.",
    "My mind and body deserve kindness and gentle care.",
    "I trust my journey and honor my changing needs.",
    "I am creating a safe, loving space for both of us.",
    # Garbha Sanskar + cortisol-calm science (Georgia Tech / Nature 2024)
    "Every calm breath I take sends peace and oxygen directly to my baby.",
    "My thoughts and feelings shape the world my baby is growing into.",
    "I choose peace today, and my baby feels it.",
    "My body knows exactly what it is doing. I trust this process completely.",
    "With each heartbeat, I send love to the little life growing inside me.",
    # Mood-adaptive compassion
    "Even on hard days, I am still nourishing my baby beautifully.",
    "I do not need to be perfect to be a wonderful mother.",
    "My gentleness with myself is a gift I give to my child.",
    "I am not alone in this. My baby and I are doing this together.",
    "This moment is enough. I am enough.",
]

# Evening whispers — for baby, changes nightly (14 items, random selection)
EVENING_WHISPERS = [
    "Today I did my best, little one.",
    "You are so loved already.",
    "We made it through today together.",
    "I am learning, and that is enough.",
    "You are safe, and so am I.",
    "Thank you for growing so beautifully.",
    "Tomorrow we get to try again.",
    "Every heartbeat of mine is a lullaby for you.",
    "I felt you with me today, even in the quiet moments.",
    "Your presence makes me braver than I ever knew I could be.",
    "Rest now, little one. We are safe, and morning is coming.",
    "I whisper this so you know: you are already so deeply wanted.",
    "The world you are coming into is full of people who will love you.",
    "I am growing into your mother, one day at a time.",
]

# Day 1: Breathing and somatic relaxation activities
BREATHING_ACTIVITIES = [
    {
        "id": "box_breathing",
        "name": "Box Breathing",
        "category": "Breathing",
        "stars": 5,
        "duration_min": 2,
        "duration_max": 5,
        "trimester_min": 1,
        "week_min": 1,
        "week_max": 42,
        "moods": ["anxious", "overwhelmed", "stressed", "agitated", "fearful"],
        "description": "A structured breathing pattern that calms the nervous system and regains focus.",
        "prompt": "Inhale for 4 seconds, hold for 4, exhale for 4, and hold for 4. Repeat this cycle.",
        "science_note": "Regulates autonomic nervous system by activating the parasympathetic branch.",
        "baby_book": "Your baby feels the steady rhythm of your heartbeat as your breathing slows down.",
        "pillar": "Calm",
    },
    {
        "id": "extended_exhale",
        "name": "Extended Exhale",
        "category": "Breathing",
        "stars": 4,
        "duration_min": 3,
        "duration_max": 6,
        "trimester_min": 1,
        "week_min": 1,
        "week_max": 42,
        "moods": ["anxious", "panicked", "restless", "frustrated"],
        "description": "Breathing where the exhalation is twice as long as the inhalation.",
        "prompt": "Inhale gently for 3 seconds, then exhale slowly through pursed lips for 6 seconds.",
        "science_note": "Extended exhalations stimulate the vagus nerve, signaling the brain to reduce heart rate.",
        "baby_book": "The gentle release of carbon dioxide brings fresh, oxygen-rich blood directly to your placenta.",
        "pillar": "Release",
    },
    {
        "id": "body_scan",
        "name": "Body Scan",
        "category": "Breathing",
        "stars": 4,
        "duration_min": 5,
        "duration_max": 10,
        "trimester_min": 1,
        "week_min": 1,
        "week_max": 42,
        "moods": ["tired", "uncomfortable", "sleepless", "overwhelmed", "tense"],
        "description": "Gently bringing awareness to each part of the body to release physical tension.",
        "prompt": "Lie or sit comfortably. Direct your breath into your toes, moving up slowly to your ankles, knees, hips, and chest.",
        "science_note": "Increases somatic awareness and reduces muscular tension associated with stress hormones.",
        "baby_book": "Releasing physical tension in your muscles allows your uterus to relax and expand naturally.",
        "pillar": "Presence",
    },
    {
        "id": "pmr",
        "name": "Progressive Muscle Relaxation",
        "category": "Breathing",
        "stars": 5,
        "duration_min": 5,
        "duration_max": 10,
        "trimester_min": 2,
        "week_min": 14,
        "week_max": 42,
        "moods": ["tense", "restless", "uncomfortable", "stressed"],
        "description": "Systematically tensing and releasing muscle groups to achieve deep relaxation.",
        "prompt": "Tense your shoulder muscles for 5 seconds, then release them completely. Notice the contrast.",
        "science_note": "Teaches the body the distinct difference between tension and relaxation, lowering baseline anxiety.",
        "baby_book": "Relaxed shoulders mean a relaxed core, providing your growing baby with a cozy environment.",
        "pillar": "Relaxation",
    },
    {
        "id": "safe_place",
        "name": "Safe Place Imagery",
        "category": "Breathing",
        "stars": 4,
        "duration_min": 4,
        "duration_max": 8,
        "trimester_min": 1,
        "week_min": 1,
        "week_max": 42,
        "moods": ["anxious", "fearful", "sad", "stressed"],
        "description": "Visualizing a peaceful place where you feel completely safe and supported.",
        "prompt": "Close your eyes and picture a place where you feel entirely safe. Engage all your senses in this space.",
        "science_note": "Mental imagery activates brain regions similar to real experience, calming the amygdala.",
        "baby_book": "When you feel safe, your body releases oxytocin, the love hormone, which flows to your baby.",
        "pillar": "Comfort",
    },
    {
        "id": "loving_kindness",
        "name": "Loving-Kindness Meditation",
        "category": "Breathing",
        "stars": 5,
        "duration_min": 3,
        "duration_max": 6,
        "trimester_min": 1,
        "week_min": 1,
        "week_max": 42,
        "moods": ["sad", "guilty", "lonely", "self-critical"],
        "description": "Directing warm, compassionate wishes to yourself and your baby.",
        "prompt": "Silently repeat: May I be happy. May my baby be healthy. May we be safe and at peace.",
        "science_note": "Increases feelings of social connection and self-compassion, decreasing negative self-talk.",
        "baby_book": "Your baby is already learning to sense the love and warmth of your maternal connection.",
        "pillar": "Connection",
    },
]

# Day 1: Journaling activities
JOURNALING_ACTIVITIES = [
    {
        "id": "free_mood_journal",
        "name": "Free Expression Mood Journal",
        "category": "Journaling",
        "description": "A blank canvas to express whatever feelings are top of mind without filters.",
        "prompt": "Write freely about whatever is on your mind right now. Let the thoughts flow.",
        "week_min": 1,
        "exclusive_with": None,
        "science_note": "Expressive writing improves psychological and physical health (PMC 2013). Reduces prenatal stress and improves mood.",
        "pillar": "Emotional release",
    },
    {
        "id": "gratitude_journal",
        "name": "Gratitude Journal",
        "category": "Journaling",
        "description": "Reflecting on positive moments or supportive elements in your life.",
        "prompt": "List three things, big or small, that you are grateful for today.",
        "week_min": 1,
        "exclusive_with": None,
        "science_note": "Shifts cognitive focus from threat to resource. Linked to lower prenatal anxiety across MBCP cohorts.",
        "pillar": "Positive affect",
    },
    {
        "id": "self_compassion",
        "name": "Self-Compassion Letter",
        "category": "Journaling",
        "description": "Writing a gentle, supportive letter to yourself as you would to a dear friend.",
        "prompt": "Write down one difficulty you faced today, followed by words of understanding and kindness to yourself.",
        "week_min": 1,
        "exclusive_with": "free_mood_journal",
        "science_note": "MBCP core practice. Reduces pain catastrophizing and fear of childbirth by 33% across RCTs.",
        "pillar": "Self-compassion",
    },
    {
        "id": "birth_wishes",
        "name": "Birth Wishes & Intentions",
        "category": "Journaling",
        "description": "Exploring hopes and preferences for your labor, birth, and early postpartum days.",
        "prompt": "Imagine your ideal birth setting. What intentions, comfort measures, or thoughts do you want to carry with you?",
        "week_min": 14,
        "exclusive_with": None,
        "science_note": "Childbirth self-efficacy is the single strongest predictor of positive birth experience (MBCP 2021 RCT).",
        "pillar": "Agency",
    },
]

# Day 1: Baby connect activities
BABY_CONNECT_ACTIVITIES = [
    {
        "id": "daily_narration",
        "name": "Daily Narration",
        "category": "Baby Connect",
        "description": "Describing your current surroundings or activities out loud to your baby.",
        "prompt": "Take a moment to narrate what you are doing, seeing, or planning next to your baby. Use a warm, melodic tone — your baby is listening.",
        "week_min": 18,
        "science_note": "Mother's voice is the predominant sensory input for the fetus (Univ. of Florida). Baby recognises familiar phrases by Week 34.",
        "pillar": "Language exposure",
    },
    {
        "id": "story_time",
        "name": "Story Time",
        "category": "Baby Connect",
        "description": "Reading a book or telling a simple story aloud so your baby can hear your voice.",
        "prompt": "Pick a favorite childhood story, a poem, or a few pages of any book you love. Read slowly and clearly to your baby. Your voice is the music.",
        "week_min": 18,
        "science_note": "Rhythmic cadence of reading calms the maternal HPA axis and familiarises the baby with speech patterns before birth.",
        "pillar": "Bonding",
    },
    {
        "id": "humming_singing",
        "name": "Humming & Singing",
        "category": "Baby Connect",
        "description": "Humming a calm melody or singing a soft lullaby to share your breath's vibration.",
        "prompt": "Hum a gentle tune or sing a lullaby you love. Rest your hand gently on your belly. Repeat the same melody daily — your baby is building memory of your voice.",
        "week_min": 18,
        "science_note": "Maternal humming transmits vibration through amniotic fluid directly to baby. Builds fetal sound memory and strengthens the bond.",
        "pillar": "Bonding",
    },
    {
        "id": "conversation_with_baby",
        "name": "Conversation with Baby",
        "category": "Baby Connect",
        "description": "Speaking directly to your baby about your hopes, love, or current thoughts.",
        "prompt": "Share a few thoughts directly with your baby. Tell them what you felt today, what you hope for them, or simply say 'I love you' — slowly and warmly.",
        "week_min": 14,
        "science_note": "Fetal heart decelerates on hearing the familiar maternal voice — a recognition signal (PubMed 2019). Strengthens prenatal attachment.",
        "pillar": "Attachment",
    },
    {
        "id": "evening_whisper",
        "name": "Evening Whisper",
        "category": "Baby Connect",
        "description": "A soft bedtime whisper to say goodnight and share a peaceful intention.",
        "prompt": "Whisper a gentle goodnight message to your baby before sleeping. You might say: 'Little one, we made it through today together. Sleep well.'",
        "week_min": 1,
        "science_note": "Consistent bedtime voice rituals build fetal memory and reinforce the maternal bond from the earliest weeks.",
        "pillar": "Bonding",
    },
]

# Day 1: Creative alternate activities
CREATIVE_ALTERNATES = [
    {
        "id": "bilateral_drawing",
        "name": "Bilateral Drawing",
        "category": "Creative Alternate",
        "description": "Drawing with both hands simultaneously to soothe the nervous system.",
        "prompt": "Take a pen in each hand. Start at the center of a page and draw matching shapes outwards — circles, waves, leaves. Let both hands move together, slowly.",
        "week_min": 1,
        "science_note": "Engages both brain hemispheres simultaneously. Calming through rhythmic bilateral movement. Helps regulate the nervous system (Expressive Monkey 2024).",
        "pillar": "Nervous system regulation",
    },
    {
        "id": "symmetry_drawing",
        "name": "Symmetry Drawing",
        "category": "Creative Alternate",
        "description": "Focusing on drawing balanced, repeating geometric patterns.",
        "prompt": "Draw a central axis down the middle of a page. Build a symmetrical mandala or nature pattern outwards from the center. There are no rules — just balance.",
        "week_min": 1,
        "science_note": "Bilateral coordination engages interhemispheric interaction, supporting focus and calm without physical exertion.",
        "pillar": "Focus",
    },
]

# Calming music activity (for tired/uncomfortable moods)
MUSIC_ACTIVITY = {
    "id": "calming_music",
    "name": "Calming Music",
    "category": "Music",
    "description": "Listening to gentle, instrumental music to relax the mind and body.",
    "prompt": "Play any soft instrumental or ambient music — whatever feels calming to you. Place your hand gently on your belly. Close your eyes and simply listen for 5–10 minutes. You do not need to do anything else.",
    "moods": ["tired", "uncomfortable"],
    "science_note": "Music modulates the fetal Autonomic Nervous System, enhancing Heart Rate Variability near term (PMC 2022). Gentle, repetitive melodies induce a parasympathetic state in both mother and baby.",
    "pillar": "Relaxation",
}

# Research-based free-text keyword overrides (from MBCP + Garbha Sanskar matrix).
# Each entry: (tuple_of_keywords, dict_of_category_to_activity_id).
# In get_daily_plan(), these override the mood-chip routing when the mother's
# free-text mentions a specific physical symptom or emotional signal.
FREE_TEXT_KEYWORD_OVERRIDES = [
    # Physical symptoms → minimal-effort, proven-effective activity
    (("nausea", "nauseous", "morning sickness", "vomiting", "sick", "queasy"),
     {"breathing": "extended_exhale"}),          # vagus nerve activation, no movement
    (("back pain", "backache", "back ache", "lower back", "round ligament",
      "aching back", "back hurts", "back is hurting", "back is paining",
      "back paining", "back hurt"),
     {"breathing": "body_scan"}),                # MBCP somatic scan for pain
    (("headache", "head pain", "migraine", "head hurts"),
     {"breathing": "box_breathing"}),            # regulated breathing for head tension
    (("can't sleep", "cant sleep", "insomnia", "not sleeping", "awake all night", "sleepless"),
     {"breathing": "body_scan"}),                # somatic scan → sleep preparation
    # Emotional signals → research-matched activity
    (("anxious", "anxiety", "panic", "overwhelmed", "stressed", "scared of birth", "scared of labour"),
     {"breathing": "safe_place"}),               # safe place imagery (amygdala calming)
    (("sad", "crying", "tears", "sobbing", "lonely", "alone", "depressed", "empty"),
     {"journaling": "self_compassion"}),         # MBCP self-compassion letter
    (("angry", "frustrat", "irritat", "rage", "furious"),
     {"journaling": "free_mood_journal"}),       # expressive release (PMC 2013)
    (("she kicked", "he kicked", "baby kicked", "felt a kick", "felt the baby", "baby moved"),
     {"baby_connect": "conversation_with_baby"}), # celebrate the moment of connection
    (("grateful", "thankful", "blessed", "content", "at peace"),
     {"journaling": "gratitude_journal"}),       # positive-affect journaling
    (("scared", "fear", "afraid", "birth fear", "worried about birth", "worried about baby"),
     {"breathing": "safe_place", "journaling": "self_compassion"}),
]

# Day 1: Preferred activities mapping based on user mood input
MOOD_TO_BREATHING = {
    "anxious": ["box_breathing", "extended_exhale", "safe_place"],
    "overwhelmed": ["box_breathing", "body_scan"],
    "stressed": ["box_breathing", "pmr", "safe_place"],
    "tired": ["body_scan"],
    "uncomfortable": ["body_scan", "pmr"],
    "sad": ["loving_kindness", "safe_place"],
    "lonely": ["loving_kindness"],
    "happy": ["loving_kindness"],
    "excited": ["box_breathing"],
    "guilty": ["loving_kindness"],
    "restless": ["extended_exhale", "pmr"],
    "tense": ["body_scan", "pmr"],
    "panicked": ["extended_exhale"],
    "frustrated": ["extended_exhale"],
    "sleepless": ["body_scan"],
    "fearful": ["box_breathing", "safe_place"],
    "self-critical": ["loving_kindness"],
}

MOOD_TO_JOURNALING = {
    "anxious": ["free_mood_journal", "gratitude_journal"],
    "overwhelmed": ["free_mood_journal"],
    "stressed": ["free_mood_journal", "gratitude_journal"],
    "tired": ["gratitude_journal"],
    "uncomfortable": ["free_mood_journal"],
    "sad": ["free_mood_journal", "self_compassion"],
    "lonely": ["self_compassion", "gratitude_journal"],
    "happy": ["gratitude_journal", "birth_wishes"],
    "excited": ["birth_wishes", "gratitude_journal"],
    "guilty": ["self_compassion"],
    "restless": ["free_mood_journal"],
    "tense": ["free_mood_journal"],
    "panicked": ["free_mood_journal"],
    "frustrated": ["free_mood_journal"],
    "sleepless": ["free_mood_journal"],
    "fearful": ["free_mood_journal", "birth_wishes"],
    "self-critical": ["self_compassion"],
}

MOOD_TO_BABY_CONNECT = {
    "anxious": ["evening_whisper", "conversation_with_baby"],
    "overwhelmed": ["evening_whisper"],
    "stressed": ["evening_whisper", "conversation_with_baby"],
    "tired": ["evening_whisper"],
    "uncomfortable": ["evening_whisper"],
    "sad": ["conversation_with_baby", "humming_singing"],
    "lonely": ["conversation_with_baby", "story_time"],
    "happy": ["daily_narration", "story_time", "humming_singing"],
    "excited": ["daily_narration", "conversation_with_baby", "story_time"],
    "guilty": ["conversation_with_baby", "evening_whisper"],
    "restless": ["humming_singing"],
    "tense": ["humming_singing"],
    "panicked": ["evening_whisper"],
    "frustrated": ["evening_whisper"],
    "sleepless": ["evening_whisper"],
    "fearful": ["conversation_with_baby", "evening_whisper"],
    "self-critical": ["conversation_with_baby"],
}

# Day 1: Pregnancy milestones for specific weeks
WEEKLY_MILESTONES = {
    4: "The blastocyst has successfully implanted in your uterine lining. Hormones are starting to rise as the foundation of your pregnancy is laid.",
    8: "Your baby's heart is beating at nearly 150 beats per minute. Tiny buds for arms and legs are forming, and facial features are starting to develop.",
    12: "The end of the first trimester approaches. Your baby is fully formed from head to toe, now kicking and moving fingers, though you can't feel it yet.",
    16: "Your baby's eyes are starting to move slowly under the lids, and they are sensitive to light. The nervous system is growing rapidly.",
    18: "Your baby can now hear your heartbeat, the rush of your blood, and even external sounds. This is a beautiful time to start connecting through sound.",
    20: "Congratulations, you've reached the halfway point! Your baby is covered in vernix, a protective coating, and you may begin feeling gentle flutters.",
    22: "Your baby's eyebrows and eyelashes are fully developed, and they are starting to develop a regular pattern of waking and sleeping.",
    24: "Your baby is now considered viable. Their inner ear is fully formed, helping them sense which way is up or down in the womb.",
    28: "Entering the third trimester! Your baby's eyes can open and close, and their lungs are beginning to practice breathing amniotic fluid.",
    32: "Your baby is gaining weight rapidly and has less space to move, so you'll feel more rolls and stretches rather than sharp kicks.",
    36: "Your baby is fully mature and may start settling into the head-down position in preparation for birth. Keep resting and nourishing yourself.",
    40: "Your baby is ready to meet the world! You have nurtured this life beautifully. Trust your body and take deep, comforting breaths.",
}
