"""Translations for PidginPharma.

Supports 6 languages:
  - pidgin: Nigerian Pidgin English (default)
  - en: Standard English
  - hausa: Hausa language
  - yoruba: Yoruba language
  - igbo: Igbo language (southeastern Nigeria)
  - edo: Edo/Bini language (Edo State/Benin City)

Each translation dict maps a key to {pidgin, en, hausa, yoruba}.

Translation source: HuggingFace Helsinki-NLP models + manual clinical
phrase curation for medical accuracy.
"""

# Intake question prompts (key -> {lang: prompt})
INTAKE_PROMPTS = {
    "intro_pidgin": {
        "pidgin": "  Let me ask you some questions about di patient make I fit help well well.",
        "en": "  Let me ask some questions about the patient to give you the best advice.",
        "hausa": "  Za na tambayi game da likitan domin na iya taimaka da kyau.",
        "yoruba": "  Mo fe be e lori si alaiso lati le lora fun yin.",
        "igbo": "  Ka m ajụjụ banyere onye a ka m enye gị enyemaka nke ọma.",
        "edo": "  Ma na gbe questions bokhon vbe ona ma rhan son khian.",
    },
    "intro_hausa": {
        "pidgin": "  (You fit say 'skip' or 'i no know' for any question wey you no get answer.)",
        "en": "  (You can say 'skip' or 'i don't know' for any question you can't answer.)",
        "hausa": "  (Za ka iya cewa 'tsallake' ko na sani ko ba ni da amsa a kowace tambaya.)",
        "yoruba": "  (O le sọ 'fi sẹlẹ' tabi 'mi o mo' fun eyikeyi ibeere ti o ko le dá.)",
        "igbo": "  (Ị nwere ike ịsị 'skip' ma ọ bụ 'a maghị' maka ajụjụ ọ bụla ị naghị eze i.",
        "edo": "  (I khian gbe 'skip' maobee 'o mi o ghiyo' vbe questions iromhe romhe.)",
    },
    "age": {
        "pidgin": "How old is di patient? (e.g. 3 years, 6 months, adult)",
        "en": "What is the patient's age? (e.g. 3 years, 6 months, adult)",
        "hausa": "Yaya shekaru nawa ne mutumin? (misali: shekaru 3, watanni 6, manya)",
        "yoruba": "Ibeere naa pe ni odo? (bii: odo 3, ose 6, agbalagba)",
        "igbo": "Onye a di afọ ole? (dịka: afọ 3, ọnwa 6, nwa nta)",
        "edo": "Ona vbe ile kilo? (bhen: ile 3, ọnwa 6, agbalagba)",
    },
    "weight": {
        "pidgin": "How heavy is di patient? (e.g. 15 kg, 70 kg). If you no know, say 'skip'.",
        "en": "What is the patient's weight? (e.g. 15 kg, 70 kg). Say 'skip' if unknown.",
        "hausa": "Yaya nauyin mutumin? (misali: kilogram 15, kilogram 70). Idan ba ka sani, cewa 'tsallake'.",
        "yoruba": "Ibeere naa pe ni iru? (bii: kilogiramu 15, kilogiramu 70). Ti o ko le, sọ 'fi sẹlẹ'.",
        "igbo": "Onye a na-ada obere ole? (dịka: kg 15, kg 70). Ọ bụrụ na ị maghị, sị 'skip'.",
        "edo": "Ona vbe ile kilo? (bhen: kg 15, kg 70). Vbe i ghi ghekhian, gbe 'skip'.",
    },
    "gender": {
        "pidgin": "Na boy or na girl?",
        "en": "Is the patient male or female?",
        "hausa": "Mutumin ne ko mace?",
        "yoruba": "Jijin ni abirin ni?",
        "igbo": "Onye a bụ nwoke ma ọ bụ nwanyị?",
        "edo": "Ona vbe onokun maobee oniyi?",
    },
    "symptoms": {
        "pidgin": "Wetin dey worry di patient? Describe di symptoms (e.g. fever, vomit, run stomach)",
        "en": "What symptoms does the patient have? (e.g. fever, vomiting, diarrhoea)",
        "hausa": "Wanne alamu ne mutumin ke da ita? (misali: zazzafa, tarin ciki, tari)",
        "yoruba": "Kini awon ami ti alaiso wa pẹlu? (bii: ina, igbẹ, arun opo)",
        "igbo": "Kedu nsogbu onye a nwere? (dịka: ọkụ ahụ, emetic, ọsọ afọ)",
        "edo": "Kedu nsogbu ona nokhu? (bhen: ọkụ ahụ, ọgbagbese, ọsọ afọ)",
    },
    "duration": {
        "pidgin": "How long e don dey like dis? (e.g. 2 days, since yesterday)",
        "en": "How long has the patient had these symptoms? (e.g. 2 days, since yesterday)",
        "hausa": "Yaya tsawon lokacin da mutumin ke da wannan? (misali: kwanaki 2, jiya daga)",
        "yoruba": "Ibi ti o pẹ ni ibi ti? (bii: ojo 2, lati ounla)",
        "igbo": "O nọ n'ụzọ n'oge kachasị nta? (dịka: ụbọchị 2, tọsịtọsị)",
        "edo": "Ona khian rhan se? (bhen: ụbọchị 2, vbe ighonghon)",
    },
    "temperature": {
        "pidgin": "You get thermometer? If yes, wetin e read? If no, say 'skip'.",
        "en": "Do you have a thermometer reading? If yes, what is it? Say 'skip' if not.",
        "hausa": "Kun sami karanta thermometar? Idan haka ne, menene? Idan ba haka ba, cewa 'tsallake'.",
        "yoruba": "Ṣe o ní igbese ina? Bí bẹ́ẹ̀ ni, kí ni ó jọ? Bí kò bá ní, sọ 'fi sẹlẹ'.",
        "igbo": "Ị nwere thermometere? Ọ bụrụ yes, kedu na-egosi? Ọ bụrụ na ezhighị, sị 'skip'.",
        "edo": "I nukhu thermometer? Vbe onokho, kheghen ona? Vbe i ghi nukhu, gbe 'skip'.",
    },
    "allergies": {
        "pidgin": "Di patient get any medicine wey e no fit take? (allergy). If none, say 'no'.",
        "en": "Does the patient have any drug allergies? Say 'no' if none.",
        "hausa": "Mutumin yana da kowane magani da bai dace ba? Idan babu, cewa 'a'a'.",
        "yoruba": "Ṣe alaiso ní eyikeyi afikun oogun? Bí kò bá ní, sọ 'bẹẹkọ'.",
        "igbo": "Onye a nwere ọgwụ ọ bụla na-adịghị mma? Ọ bụrụ na ezhighị, sị 'mba'.",
        "edo": "Ona nukhu medicine iromhe? Vbe i ghi nukhu, gbe 'o khe'.",
    },
    "pregnant": {
        "pidgin": "Na woman of childbearing age? If yes, she don born before or she fit dey pregnant?",
        "en": "Is this a woman of childbearing age? Could she be pregnant?",
        "hausa": "Wanne mace ce da shekaru na haihuwa? Idan haka ne, ta ta haifi yaro ko ta yi ciki?",
        "yoruba": "Ṣe iyá ni obi ni ọmọ? Bí bẹẹ̀ ni, ṣe ọmọ ti i wá tabi ṣe ó lè ní ọmọ?",
        "igbo": "Onye a bụ nwanyị nke nwere afọ ime? Ọ bụrụ yes, ọ nwetara bekee ma ọ bụ nwere ime?",
        "edo": "Ona vbe oniyi na evba ime? Vbe onokho, ona tighen ona bekee maobee ona evba ime?",
    },
    "current_meds": {
        "pidgin": "Di patient dey take any medicine now? (e.g. paracetamol, amoxicillin). If none, say 'no'.",
        "en": "Is the patient currently taking any medications? Say 'no' if none.",
        "hausa": "Mutumin yana cin kowane magani yanzu? (misali: paracetamol, amoxicillin). Idan babu, cewa 'a'a'.",
        "yoruba": "Ṣe alaiso ní oogun kankan lọwọlọwọ? Bí kò bá ní, sọ 'bẹẹkọ'.",
        "igbo": "Onye a na-ewere ọgwụ ọ bụla ugbu a? Ọ bụrụ na ezhighị, sị 'mba'.",
        "edo": "Ona kpa medicine romhion? Vbe i ghi nukhu, gbe 'o khe'.",
    },
    "history": {
        "pidgin": "Di patient get any long-term sickness? (e.g. asthma, diabetes, HIV). If none, say 'no'.",
        "en": "Does the patient have any chronic conditions? (e.g. asthma, diabetes, HIV). Say 'no' if none.",
        "hausa": "Mutumin yana da kowane cutar da ta tsawo? (misali: asthma, diabetes, HIV). Idan babu, cewa 'a'a'.",
        "yoruba": "Ṣe alaiso ní eyikeyi arun ti ó pẹ? (bii: asthma, diabetes, HIV). Bí kò bá ní, sọ 'bẹẹkọ'.",
        "igbo": "Onye a nwere ọrịa mgbe niile? (dịka: asma, sugar, HIV). Ọ bụrụ na ezhighị, sị 'mba'.",
        "edo": "Ona nukhu ọrịa khian rhan? (bhen: asma, sugar, HIV). Vbe i ghi nukhu, gbe 'o khe'.",
    },
    "pulse": {
        "pidgin": "You fit feel im pulse? If yes, how e dey? (e.g. fast, normal, 110). If no, say 'skip'.",
        "en": "Can you feel the patient's pulse? How is it? (e.g. fast, normal, 110 bpm). Say 'skip' if unknown.",
        "hausa": "Kun iya ji tsarin jinin mutumin? Yaya? (misali: sauri, na yau, 110 bpm). Idan ba ka sani, cewa 'tsallake'.",
        "yoruba": "Ṣe o lè rí ipa ẹ̀jẹ̀ alaiso? Bawo ni ó rí? (bii: kikedun, daadaa, 110 bpm). Bí o ko le, sọ 'fi sẹlẹ'.",
        "igbo": "Ị nwere ike ịna ọbara ọbara onye a? Ọ dị ka okenye? (dịka: ngwa ngwa, ka mma, 110). Ọ bụrụ na ị maghị, sị 'skip'.",
        "edo": "I khian ghe pulse vbe ona? (bhen: ngwa ngwa, ma, 110). Vbe i ghi ghekhian, gbe 'skip'.",
    },
    "respiratory_rate": {
        "pidgin": "How e dey breathe? (e.g. normal, fast, hard). If no thermometer, say 'skip'.",
        "en": "How is the patient breathing? (e.g. normal, fast, difficult). Say 'skip' if unknown.",
        "hausa": "Yaya mutumin ke numfashi? (misali: na yau, sauri, mai wuyar). Idan ba ka sani, cewa 'tsallake'.",
        "yoruba": "Bawo ni alaiso fi ń mí sí? (bii: daadaa, kikedun, ire). Bí o ko le, sọ 'fi sẹlẹ'.",
        "igbo": "Kedu ka onye a na-ebe? (dịka: ka mma, ngwa ngwa, siri ike). Ọ bụrụ na ị maghị, sị 'skip'.",
        "edo": "Ona bhe se? (bhen: ma, ngwa ngwa, da). Vbe i ghi ghekhian, gbe 'skip'.",
    },
    "spo2": {
        "pidgin": "You get oxygen meter (oximeter)? If yes, wetin e read? If no, say 'skip'.",
        "en": "Do you have a pulse oximeter? If yes, what does it read? Say 'skip' if not available.",
        "hausa": "Kun sami na'urar oxygen (oximeter)? Idan haka ne, menene karantawa? Idan ba haka ba, cewa 'tsallake'.",
        "yoruba": "Ṣe o ní igbese afẹfẹ (oximeter)? Bí bẹẹ̀ ni, kí ni ó jọ? Bí kò bá ní, sọ 'fi sẹlẹ'.",
        "igbo": "Ị nwere oxygen meter (oximeter)? Ọ bụrụ yes, kedu na-egosi? Ọ bụrụ na ezhighị, sị 'skip'.",
        "edo": "I nukhu oxygen meter (oximeter)? Vbe onokho, kheghen ona? Vbe i ghi nukhu, gbe 'skip'.",
    },
}

# Summary confirmation
SUMMARY = {
    "pidgin": "  OK, I don hear. Patient info: {summary}",
    "en": "  OK, got it. Patient info: {summary}",
    "hausa": "  OK, na ji. Bayanan mutumin: {summary}",
    "yoruba": "  OK, mo ti gbọ. Alaye alaiso: {summary}",
    "igbo": "  OK, a ma m aka. Ozi onye a: {summary}",
    "edo": "  OK, o ya. Vbe ona: {summary}",
}

# Loading messages (shown while processing)
LOADING_MESSAGES = {
    "pidgin": [
        "Please wait... I dey check the official guidelines for you.",
        "Hold on small... I dey look through the treatment book.",
        "Just a moment... I dey search for the right medicine info.",
        "One second... I dey check the drug interaction table for you.",
        "Hold on... I dey find di best answer from di Nigeria guidelines.",
    ],
    "en": [
        "Please wait... Checking the official guidelines for you.",
        "Hold on... Looking through the treatment guidelines.",
        "Just a moment... Searching for the right medicine information.",
        "One second... Checking the drug interaction database.",
        "Hold on... Finding the best answer from Nigerian clinical guidelines.",
    ],
    "hausa": [
        "Da fatan za a jira... Na ke duba ka'idojin hukuma gare ku.",
        "Jira kaɗan... Na ke duba littafin magani.",
        "Ji daɗaɗɗa... Na ke neman bayanan magani da dace.",
        "Ɗaya daƙiƙa... Na ke duba taswirar hadakar magani.",
        "Jira... Na ke neman mafi kyawun amsa daga ka'idojin Likitancin Nijeriya.",
    ],
    "yoruba": [
        "Jọwọ jú... Mo ń wá àwọn ìlànà ìṣègùn fún ẹ.",
        "Dúró di ẹ́... Mo ń wo ìwé ìṣègùn.",
        "Kíán ọ̀pọ̀lọpọ̀... Mo ń wá alaye oogun tó péye.",
        "Ìsẹjú kan... Mo ń wo àpẹẹrẹ ìṣatapọ̀ oogun.",
        "Dúró... Mo ń wá dáhùn tó dára jù lọ láti inú àwọn ìlànà Ìṣègùn Nàìjíríà.",
    ],
    "igbo": [
        "Chọrọ nchebe... Ka m na-achọ ụzọ dịka ọkwa na-eduzi.",
        "Nọrọ n'oge... Ka m na-ahụ n'okpuru ọgwụ.",
        "Oge nkenke... Ka m na-achọ ozi ọgwụ doro anya.",
        "Ibi otu... Ka m na-enyocha Table ọgwụ na-agbanwe.",
        "Nọrọ n'oge... Ka m na-achọ azịza kachasị mma site na ntuziaka Ahụike Naijiria.",
    ],
    "edo": [
        "Rie n'ile... Ma na check guidelines vbe official khian.",
        "Rie nosa... Ma na look through treatment book khian.",
        "Kian khian... Ma na search medicine info khian.",
        "Ighen otu... Ma na check drug interaction table khian.",
        "Rie nosa... Ma na get best answer vbe Nigeria guidelines khian.",
    ],
}

# Common clinical responses
RESPONSES = {
    "no_services": {
        "pidgin": (
            "Sorry - the offline model and data server no dey reachable now. "
            "Run `start.ps1` or `bash start.sh` make dem start.\n\n"
            "If e be emergency, send di patient go hospital now now."
        ),
        "en": (
            "Sorry - the offline model and data server are not reachable now. "
            "Run `start.ps1` or `bash start.sh` to start them.\n\n"
            "If this is an emergency, refer the patient to hospital immediately."
        ),
        "hausa": (
            "Yi basira - model na offline da sufetar bayanai ba za a iya samun su ba yanzu. "
            "Gudu `start.ps1` ko `bash start.sh` don fara su.\n\n"
            "Idan wannan taimako ne, a tsara mutumin zuwa asibitace nan take.",
        ),
        "yoruba": (
            "Jọwọ bí... model offline ati abala data ko le rí sí báyìí. "
            "Ṣí `start.ps1` tàbí `bash start.sh` láti bẹ̀rẹ̀ wọn.\n\n",
            "Bí ẹ̀yìn bá jẹ́ ohun pàtàkì, fi alaiso sí ilé ìsọ̀gùn lẹ́ẹ̀kan náà.",
        ),
        "igbo": (
            "Nnọ - offline model na data server adịghị n'ebe a ugbu a. "
            "Bido `start.ps1` ma ọ bụ `bash start.sh` ka ha bido.\n\n"
            "Ọ bụrụ na o ji oge ji, zigara onye a ụlọọrụ ahụike."
        ),
        "edo": (
            "Nokhu - offline model na data server o khe si khian vbe here. "
            "Bido `start.ps1` maobee `bash start.sh` ma na bido vbe.\n\n"
            "Vbe o khe emergency, ze ona vbe hospital ngwangwa."
        ),
    },
    "emergency_referral": {
        "pidgin": "⚠️ REFERRAL: Send di patient go hospital NOW NOW. This one no fit wait.",
        "en": "⚠️ REFERRAL: Refer the patient to hospital IMMEDIATELY. This cannot wait.",
        "hausa": "⚠️ BADA Shawara: Aika mutumin zuwa asibitace NAN TAKE. Wannan ba zai iya jira ba.",
        "yoruba": "⚠️ ÌGBÉKÉLẸ̀: Fi alaiso sí ilé ìsọ̀gùn LÉẸ̀KAN NÁÀ. Èyí kò lè dúró.",
        "igbo": "⚠️ NZUKO: Zigara onye a ụlọ ọrụ ahụike OZUGBO. Nke a adịghị nchebe.",
        "edo": "⚠️ REFERRAL: Ze ona vbe hospital NGWANGWA. Ona o khe rie.",
    },
    "iv_fluid_needed": {
        "pidgin": "💧 DRIP NEEDED: Di patient need IV fluid. Make sure say you get Normal Saline or Ringer Lactate. Give as prescribed.",
        "en": "💧 IV FLUIDS NEEDED: The patient requires intravenous fluids. Ensure Normal Saline or Ringer Lactate is available.",
        "hausa": "💧 BAMAN KWAURACI: Mutumin yana buƙatar ruwan cikin jini. Tabbatar cewa an sami Normal Saline ko Ringer Lactate.",
        "yoruba": "💧 ÌFỌ̀N MIMỌ́ TÍ Á BÁ NÍ: Alaiso nílò omi inú ẹ̀jẹ̀. Jẹ́ kí ó jẹ́ pé Normal Saline tàbí Ringer Lactate wà níbùgbé.",
        "igbo": "💧 A CHỌRỌ DRIP: Onye a chọrọ IV fluid. Nwee ike izipụta Normal Saline ma ọ bụ Ringer Lactate.",
        "edo": "💧 DRIP BEKHIAN: Ona nukhu IV fluid. Kheghen Normal Saline maobee Ringer Lactate si khian.",
    },
    "symptom_detected": {
        "pidgin": "I see say this na patient problem. Make I ask some questions first.",
        "en": "I see this is a patient problem. Let me ask some questions first.",
        "hausa": "Na ga cewa wannan matsalar mutumin ne. Bari na tambayi wasu tambayi da fari.",
        "yoruba": "Mo ri pe eyi jo bisile alaiso. Jo ki a bere pelu awon ibeere keyin.",
        "igbo": "A hụ na nsogbu onye a. Ka m ajụjụ ọ bụla mbụ.",
        "edo": "O ya na ona nukhu questions. Ma na bokhon questions nosa.",
    },
}

# Red flag messages
RED_FLAGS = {
    "fever_infant": {
        "pidgin": "⚠️ RED FLAG: Hot body for pikin wey no pass 3 months - SEND HOSPITAL NOW",
        "en": "⚠️ RED FLAG: Fever in infant (<3 months) - REFER IMMEDIATELY",
        "hausa": "⚠️ ALAMA: Zazzafa a jariri (<3 watanni) - AIKA ASIBITACE NAN TAKE",
        "yoruba": "⚠️ AMI PÀTÁKÌ: Ina nínú ọmọ kékèké (<3 oṣù) - FI SÍ ILÉ ÌSỌ̀GÙN LÉẸ̀KAN NÁÀ",
        "igbo": "⚠️ NKU EZE: Ọkụ ahụ na nwa nta (<3 ọnwa) - ZIGARA ỤLỌ ỌRỤ AHỤIKE",
        "edo": "⚠️ ALAMA: Ọkụ ahụ vbe ona nta (<3 ọnwa) - ZE HOSPITAL NGWANGWA",
    },
    "spo2_low": {
        "pidgin": "⚠️ RED FLAG: Oxygen don low well well (SpO2 <90%) - SEND HOSPITAL NOW",
        "en": "⚠️ RED FLAG: Severe hypoxia (SpO2 <90%) - REFER IMMEDIATELY",
        "hausa": "⚠️ ALAMA: Rashin iskar oxygen (SpO2 <90%) - AIKA ASIBITACE NAN TAKE",
        "yoruba": "⚠️ AMI PÀTÁKÌ: Pàtẹ́kun afẹfẹ (SpO2 <90%) - FI SÍ ILÉ ÌSỌ̀GÙN LÉẸ̀KAN NÁÀ",
        "igbo": "⚠️ NKU EZE: Mgbu Oxygen (SpO2 <90%) - ZIGARA ỤLỌ ỌRỤ AHỤIKE OZUGBO",
        "edo": "⚠️ ALAMA: Oxygen si n'ile (SpO2 <90%) - ZE HOSPITAL NGWANGWA",
    },
    "fast_breathing_child": {
        "pidgin": "⚠️ RED FLAG: Pikin dey breathe fast (fit be pneumonia) - SEND HOSPITAL",
        "en": "⚠️ RED FLAG: Fast breathing in child (possible pneumonia) - REFER",
        "hausa": "⚠️ ALAMA: Saurin numfashi a yaro (zai iya zama pneumonia) - AIKA ASIBITACE",
        "yoruba": "⚠️ AMI PÀTÁKÌ: Mímú kikedun nínú ọmọ (ó lè jẹ́ pneumonia) - FI SÍ ILÉ ÌSỌ̀GÙN",
        "igbo": "⚠️ NKU EZE: Onye a na-ebe ngwa ngwa (nwere ike ị bụ pneumonia) - ZIGARA ỤLỌ ỌRỤ AHỤIKE",
        "edo": "⚠️ ALAMA: Ona bhe ngwa ngwa (o khian vbe pneumonia) - ZE HOSPITAL",
    },
    "dehydration_severe": {
        "pidgin": "⚠️ RED FLAG: Severe dehydration - Patient need DRIP (IV fluid) NOW",
        "en": "⚠️ RED FLAG: Severe dehydration - Patient needs IV fluids IMMEDIATELY",
        "hausa": "⚠️ ALAMA: Rashin ruwa mai girma - Mutumin yana buƙatar BAMAN KWAURACI NAN TAKE",
        "yoruba": "⚠️ AMI PÀTÁKÌ: Ìfẹ̀rọ̀ omi púpọ̀ - Alaiso nílò ÌFỌ̀N MIMỌ́ LÉẸ̀KAN NÁÀ",
        "igbo": "⚠️ NKU EZE: Mgbu mmiri ukwuu - Onye a chọrọ DRIP (IV fluid) OZUGBO",
        "edo": "⚠️ ALAMA: Misiemien n'ile ukpọ - Ona nukhu DRIP (IV fluid) NGWANGWA",
    },
}

# IV Fluid guidance
IV_GUIDANCE = {
    "pidgin": {
        "normal_saline": "💧 Normal Saline (0.9% NaCl): Give 20-30 ml/kg over 1 hour for dehydration. Can repeat.",
        "ringer_lactate": "💧 Ringer Lactate: Give 20-30 ml/kg over 1 hour. Good for all ages.",
        "ors_drip": "💧 ORS by nasogastric tube: If patient no fit drink, give ORS through thin tube for nose.",
        "maintenance": "💧 Maintenance IV: 60 ml/kg/day for first 10kg + 30 ml/kg/day for next 10kg + 20 ml/kg/day thereafter.",
    },
    "en": {
        "normal_saline": "💧 Normal Saline (0.9% NaCl): 20-30 ml/kg over 1 hour for dehydration. May repeat.",
        "ringer_lactate": "💧 Ringer Lactate: 20-30 ml/kg over 1 hour. Suitable for all ages.",
        "ors_drip": "💧 ORS by nasogastric tube: If patient cannot drink, administer ORS via NG tube.",
        "maintenance": "💧 Maintenance IV: 60 ml/kg/day for first 10kg + 30 ml/kg/day for next 10kg + 20 ml/kg/day thereafter.",
    },
    "hausa": {
        "normal_saline": "💧 Normal Saline (0.9% NaCl): Ba 20-30 ml/kg cikin awa 1 don rashin ruwa. Za a iya sake.",
        "ringer_lactate": "💧 Ringer Lactate: Ba 20-30 ml/kg cikin awa 1. Ya dace da kowace shekaru.",
        "ors_drip": "💧 ORS ta tufafin hanci: Idan mutumin bai iya shan ba, ba ORS ta_tufafin_tufafin.",
        "maintenance": "💧 maintenance IV: 60 ml/kg/day na kwanaki 10 + 30 ml/kg/day na kwanaki 10 + 20 ml/kg/day daga.",
    },
    "yoruba": {
        "normal_saline": "💧 Normal Saline (0.9% NaCl): Fún 20-30 ml/kg nínú ìṣẹ́jú kan fún ìfẹ̀rọ̀ omi. Lè tún fún sí i.",
        "ringer_lactate": "💧 Ringer Lactate: Fún 20-30 ml/kg nínú ìṣẹ́jú kan. Tó péye fun gbogbo odo.",
        "ors_drip": "💧 ORS pẹ̀lú túbù nínú imú: Bí alaiso kò lè mu, fún ORS pẹ̀lú túbù kékèké nínú imú.",
        "maintenance": "💧 IV ìtọ́jú: 60 ml/kg/ọjọ́ fun àkọ́kọ́ 10kg + 30 ml/kg/ọjọ́ fun ìkẹ́yìn 10kg + 20 ml/kg/ọjọ́ lẹ́yìn.",
    "igbo": {
        "normal_saline": "💧 Normal Saline (0.9% NaCl): nye 20-30 ml/kg n'ụbọchị 1 maka mgbu mmiri. Ị nwere ike ịkwalite.",
        "ringer_lactate": "💧 Ringer Lactate: nye 20-30 ml/kg n'ụbọchị 1. Dị mma maka afọ niile.",
        "ors_drip": "💧 ORS site na tube akpụkpọ ụkwụ: Ọ bụrụ na onye a maghị ịṅụ, nye ORS site na tube di n'ime imi.",
        "maintenance": "💧 Maintenance IV: 60 ml/kg/day maka mbụ 10kg + 30 ml/kg/day maka nke 10kg ọzọ + 20 ml/kg/day mgbe niile.",
    },
    "edo": {
        "normal_saline": "💧 Normal Saline (0.9% NaCl): nye 20-30 ml/kg n'ubokhian 1 vbe misi nile. I khian re.",
        "ringer_lactate": "💧 Ringer Lactate: nye 20-30 ml/kg n'ubokhian 1. Ma vbe afokhan romhe.",
        "ors_drip": "💧 ORS vbe tube nose: Vbe ona o khian mu, nye ORS vbe tube n'ime nose.",
        "maintenance": "💧 Maintenance IV: 60 ml/kg/day vbe ubokhian 10kg + 30 ml/kg/day vbe ubokhian 10kg + 20 ml/kg/day rhan nosa.",
    },
    },
}


def get_intake_prompt(key: str, lang: str = "pidgin") -> str:
    """Get an intake question prompt in the requested language."""
    prompts = INTAKE_PROMPTS.get(key, {})
    return prompts.get(lang, prompts.get("pidgin", prompts.get("en", key)))


def get_loading_messages(lang: str = "pidgin") -> list[str]:
    """Get loading messages in the requested language."""
    return LOADING_MESSAGES.get(lang, LOADING_MESSAGES["pidgin"])


def get_response(key: str, lang: str = "pidgin") -> str:
    """Get a clinical response in the requested language."""
    msgs = RESPONSES.get(key, {})
    return msgs.get(lang, msgs.get("pidgin", msgs.get("en", key)))


def get_red_flag(key: str, lang: str = "pidgin") -> str:
    """Get a red flag message in the requested language."""
    flags = RED_FLAGS.get(key, {})
    return flags.get(lang, flags.get("pidgin", flags.get("en", key)))


def get_summary(lang: str = "pidgin") -> str:
    """Get the summary confirmation template."""
    template = SUMMARY.get(lang, SUMMARY["pidgin"])
    return template


def get_iv_guidance(key: str, lang: str = "pidgin") -> str:
    """Get IV fluid guidance in the requested language."""
    guides = IV_GUIDANCE.get(lang, IV_GUIDANCE["pidgin"])
    return guides.get(key, key)
