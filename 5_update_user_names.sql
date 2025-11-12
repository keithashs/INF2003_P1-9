-- ============================================================================
-- UPDATE ALL USERS WITH REALISTIC NAMES AND EMAILS
-- This script adds realistic names and emails for all 674 users
-- Mix of male and female names from various backgrounds
-- Email domains: @gmail.com, @hotmail.com, @outlook.com
-- ============================================================================

USE movies_db;

-- Users 3-22 (original set)
UPDATE users SET username = 'emma_wilson', email = 'emma.wilson@gmail.com' WHERE userId = 3;
UPDATE users SET username = 'james_chen', email = 'james.chen@hotmail.com' WHERE userId = 4;
UPDATE users SET username = 'sophia_garcia', email = 'sophia.garcia@outlook.com' WHERE userId = 5;
UPDATE users SET username = 'liam_patel', email = 'liam.patel@gmail.com' WHERE userId = 6;
UPDATE users SET username = 'olivia_kim', email = 'olivia.kim@gmail.com' WHERE userId = 7;
UPDATE users SET username = 'noah_rodriguez', email = 'noah.rodriguez@hotmail.com' WHERE userId = 8;
UPDATE users SET username = 'ava_nguyen', email = 'ava.nguyen@outlook.com' WHERE userId = 9;
UPDATE users SET username = 'ethan_singh', email = 'ethan.singh@gmail.com' WHERE userId = 10;
UPDATE users SET username = 'isabella_lee', email = 'isabella.lee@gmail.com' WHERE userId = 11;
UPDATE users SET username = 'mason_brown', email = 'mason.brown@hotmail.com' WHERE userId = 12;
UPDATE users SET username = 'mia_davis', email = 'mia.davis@outlook.com' WHERE userId = 13;
UPDATE users SET username = 'lucas_martinez', email = 'lucas.martinez@gmail.com' WHERE userId = 14;
UPDATE users SET username = 'charlotte_taylor', email = 'charlotte.taylor@gmail.com' WHERE userId = 15;
UPDATE users SET username = 'aiden_thomas', email = 'aiden.thomas@hotmail.com' WHERE userId = 16;
UPDATE users SET username = 'amelia_white', email = 'amelia.white@outlook.com' WHERE userId = 17;
UPDATE users SET username = 'jackson_harris', email = 'jackson.harris@gmail.com' WHERE userId = 18;
UPDATE users SET username = 'harper_clark', email = 'harper.clark@gmail.com' WHERE userId = 19;
UPDATE users SET username = 'sebastian_lewis', email = 'sebastian.lewis@hotmail.com' WHERE userId = 20;
UPDATE users SET username = 'evelyn_walker', email = 'evelyn.walker@outlook.com' WHERE userId = 21;
UPDATE users SET username = 'jack_hall', email = 'jack.hall@gmail.com' WHERE userId = 22;

-- Users 23-100
UPDATE users SET username = 'maya_johnson', email = 'maya.johnson@gmail.com' WHERE userId = 23;
UPDATE users SET username = 'daniel_wong', email = 'daniel.wong@hotmail.com' WHERE userId = 24;
UPDATE users SET username = 'sarah_anderson', email = 'sarah.anderson@outlook.com' WHERE userId = 25;
UPDATE users SET username = 'ryan_kumar', email = 'ryan.kumar@gmail.com' WHERE userId = 26;
UPDATE users SET username = 'grace_martin', email = 'grace.martin@gmail.com' WHERE userId = 27;
UPDATE users SET username = 'tyler_brooks', email = 'tyler.brooks@hotmail.com' WHERE userId = 28;
UPDATE users SET username = 'hannah_cooper', email = 'hannah.cooper@outlook.com' WHERE userId = 29;
UPDATE users SET username = 'alex_rivera', email = 'alex.rivera@gmail.com' WHERE userId = 30;
UPDATE users SET username = 'lily_peterson', email = 'lily.peterson@gmail.com' WHERE userId = 31;
UPDATE users SET username = 'marcus_james', email = 'marcus.james@hotmail.com' WHERE userId = 32;
UPDATE users SET username = 'chloe_bailey', email = 'chloe.bailey@outlook.com' WHERE userId = 33;
UPDATE users SET username = 'jordan_mills', email = 'jordan.mills@gmail.com' WHERE userId = 34;
UPDATE users SET username = 'zoe_collins', email = 'zoe.collins@gmail.com' WHERE userId = 35;
UPDATE users SET username = 'nathan_gray', email = 'nathan.gray@hotmail.com' WHERE userId = 36;
UPDATE users SET username = 'emily_foster', email = 'emily.foster@outlook.com' WHERE userId = 37;
UPDATE users SET username = 'dylan_hughes', email = 'dylan.hughes@gmail.com' WHERE userId = 38;
UPDATE users SET username = 'rachel_coleman', email = 'rachel.coleman@gmail.com' WHERE userId = 39;
UPDATE users SET username = 'kevin_jenkins', email = 'kevin.jenkins@hotmail.com' WHERE userId = 40;
UPDATE users SET username = 'anna_perry', email = 'anna.perry@outlook.com' WHERE userId = 41;
UPDATE users SET username = 'brandon_powell', email = 'brandon.powell@gmail.com' WHERE userId = 42;
UPDATE users SET username = 'natalie_long', email = 'natalie.long@gmail.com' WHERE userId = 43;
UPDATE users SET username = 'justin_patterson', email = 'justin.patterson@hotmail.com' WHERE userId = 44;
UPDATE users SET username = 'victoria_hughes', email = 'victoria.hughes@outlook.com' WHERE userId = 45;
UPDATE users SET username = 'austin_reed', email = 'austin.reed@gmail.com' WHERE userId = 46;
UPDATE users SET username = 'madison_cox', email = 'madison.cox@gmail.com' WHERE userId = 47;
UPDATE users SET username = 'cameron_howard', email = 'cameron.howard@hotmail.com' WHERE userId = 48;
UPDATE users SET username = 'julia_ward', email = 'julia.ward@outlook.com' WHERE userId = 49;
UPDATE users SET username = 'connor_torres', email = 'connor.torres@gmail.com' WHERE userId = 50;
UPDATE users SET username = 'abigail_peterson', email = 'abigail.peterson@gmail.com' WHERE userId = 51;
UPDATE users SET username = 'adam_gray', email = 'adam.gray@hotmail.com' WHERE userId = 52;
UPDATE users SET username = 'samantha_ramirez', email = 'samantha.ramirez@outlook.com' WHERE userId = 53;
UPDATE users SET username = 'jason_james', email = 'jason.james@gmail.com' WHERE userId = 54;
UPDATE users SET username = 'bella_watson', email = 'bella.watson@gmail.com' WHERE userId = 55;
UPDATE users SET username = 'nicholas_brooks', email = 'nicholas.brooks@hotmail.com' WHERE userId = 56;
UPDATE users SET username = 'sophie_kelly', email = 'sophie.kelly@outlook.com' WHERE userId = 57;
UPDATE users SET username = 'zachary_sanders', email = 'zachary.sanders@gmail.com' WHERE userId = 58;
UPDATE users SET username = 'claire_price', email = 'claire.price@gmail.com' WHERE userId = 59;
UPDATE users SET username = 'elijah_bennett', email = 'elijah.bennett@hotmail.com' WHERE userId = 60;
UPDATE users SET username = 'lucy_wood', email = 'lucy.wood@outlook.com' WHERE userId = 61;
UPDATE users SET username = 'henry_ross', email = 'henry.ross@gmail.com' WHERE userId = 62;
UPDATE users SET username = 'stella_henderson', email = 'stella.henderson@gmail.com' WHERE userId = 63;
UPDATE users SET username = 'oliver_coleman', email = 'oliver.coleman@hotmail.com' WHERE userId = 64;
UPDATE users SET username = 'aurora_jenkins', email = 'aurora.jenkins@outlook.com' WHERE userId = 65;
UPDATE users SET username = 'leo_perry', email = 'leo.perry@gmail.com' WHERE userId = 66;
UPDATE users SET username = 'hazel_powell', email = 'hazel.powell@gmail.com' WHERE userId = 67;
UPDATE users SET username = 'carter_long', email = 'carter.long@hotmail.com' WHERE userId = 68;
UPDATE users SET username = 'violet_patterson', email = 'violet.patterson@outlook.com' WHERE userId = 69;
UPDATE users SET username = 'wyatt_hughes', email = 'wyatt.hughes@gmail.com' WHERE userId = 70;
UPDATE users SET username = 'nora_reed', email = 'nora.reed@gmail.com' WHERE userId = 71;
UPDATE users SET username = 'owen_cox', email = 'owen.cox@hotmail.com' WHERE userId = 72;
UPDATE users SET username = 'ellie_howard', email = 'ellie.howard@outlook.com' WHERE userId = 73;
UPDATE users SET username = 'gabriel_ward', email = 'gabriel.ward@gmail.com' WHERE userId = 74;
UPDATE users SET username = 'aria_torres', email = 'aria.torres@gmail.com' WHERE userId = 75;
UPDATE users SET username = 'miles_peterson', email = 'miles.peterson@hotmail.com' WHERE userId = 76;
UPDATE users SET username = 'scarlett_gray', email = 'scarlett.gray@outlook.com' WHERE userId = 77;
UPDATE users SET username = 'logan_ramirez', email = 'logan.ramirez@gmail.com' WHERE userId = 78;
UPDATE users SET username = 'penelope_james', email = 'penelope.james@gmail.com' WHERE userId = 79;
UPDATE users SET username = 'eli_watson', email = 'eli.watson@hotmail.com' WHERE userId = 80;
UPDATE users SET username = 'layla_brooks', email = 'layla.brooks@outlook.com' WHERE userId = 81;
UPDATE users SET username = 'isaac_kelly', email = 'isaac.kelly@gmail.com' WHERE userId = 82;
UPDATE users SET username = 'riley_sanders', email = 'riley.sanders@gmail.com' WHERE userId = 83;
UPDATE users SET username = 'mateo_price', email = 'mateo.price@hotmail.com' WHERE userId = 84;
UPDATE users SET username = 'zoey_bennett', email = 'zoey.bennett@outlook.com' WHERE userId = 85;
UPDATE users SET username = 'lincoln_wood', email = 'lincoln.wood@gmail.com' WHERE userId = 86;
UPDATE users SET username = 'nova_ross', email = 'nova.ross@gmail.com' WHERE userId = 87;
UPDATE users SET username = 'theo_henderson', email = 'theo.henderson@hotmail.com' WHERE userId = 88;
UPDATE users SET username = 'elena_coleman', email = 'elena.coleman@outlook.com' WHERE userId = 89;
UPDATE users SET username = 'asher_jenkins', email = 'asher.jenkins@gmail.com' WHERE userId = 90;
UPDATE users SET username = 'maya_perry', email = 'maya.perry@gmail.com' WHERE userId = 91;
UPDATE users SET username = 'levi_powell', email = 'levi.powell@hotmail.com' WHERE userId = 92;
UPDATE users SET username = 'willow_long', email = 'willow.long@outlook.com' WHERE userId = 93;
UPDATE users SET username = 'hunter_patterson', email = 'hunter.patterson@gmail.com' WHERE userId = 94;
UPDATE users SET username = 'ivy_hughes', email = 'ivy.hughes@gmail.com' WHERE userId = 95;
UPDATE users SET username = 'landon_reed', email = 'landon.reed@hotmail.com' WHERE userId = 96;
UPDATE users SET username = 'ruby_cox', email = 'ruby.cox@outlook.com' WHERE userId = 97;
UPDATE users SET username = 'colton_howard', email = 'colton.howard@gmail.com' WHERE userId = 98;
UPDATE users SET username = 'paisley_ward', email = 'paisley.ward@gmail.com' WHERE userId = 99;
UPDATE users SET username = 'parker_torres', email = 'parker.torres@hotmail.com' WHERE userId = 100;

-- Users 101-200
UPDATE users SET username = 'skylar_anderson', email = 'skylar.anderson@outlook.com' WHERE userId = 101;
UPDATE users SET username = 'chase_mitchell', email = 'chase.mitchell@gmail.com' WHERE userId = 102;
UPDATE users SET username = 'brooklyn_carter', email = 'brooklyn.carter@gmail.com' WHERE userId = 103;
UPDATE users SET username = 'adrian_roberts', email = 'adrian.roberts@hotmail.com' WHERE userId = 104;
UPDATE users SET username = 'savannah_turner', email = 'savannah.turner@outlook.com' WHERE userId = 105;
UPDATE users SET username = 'blake_phillips', email = 'blake.phillips@gmail.com' WHERE userId = 106;
UPDATE users SET username = 'natalia_campbell', email = 'natalia.campbell@gmail.com' WHERE userId = 107;
UPDATE users SET username = 'jaxon_evans', email = 'jaxon.evans@hotmail.com' WHERE userId = 108;
UPDATE users SET username = 'luna_edwards', email = 'luna.edwards@outlook.com' WHERE userId = 109;
UPDATE users SET username = 'carson_collins', email = 'carson.collins@gmail.com' WHERE userId = 110;
UPDATE users SET username = 'alice_stewart', email = 'alice.stewart@gmail.com' WHERE userId = 111;
UPDATE users SET username = 'hudson_sanchez', email = 'hudson.sanchez@hotmail.com' WHERE userId = 112;
UPDATE users SET username = 'clara_morris', email = 'clara.morris@outlook.com' WHERE userId = 113;
UPDATE users SET username = 'easton_rogers', email = 'easton.rogers@gmail.com' WHERE userId = 114;
UPDATE users SET username = 'audrey_cook', email = 'audrey.cook@gmail.com' WHERE userId = 115;
UPDATE users SET username = 'axel_morgan', email = 'axel.morgan@hotmail.com' WHERE userId = 116;
UPDATE users SET username = 'aaliyah_bell', email = 'aaliyah.bell@outlook.com' WHERE userId = 117;
UPDATE users SET username = 'evan_murphy', email = 'evan.murphy@gmail.com' WHERE userId = 118;
UPDATE users SET username = 'lydia_bailey', email = 'lydia.bailey@gmail.com' WHERE userId = 119;
UPDATE users SET username = 'xavier_rivera', email = 'xavier.rivera@hotmail.com' WHERE userId = 120;
UPDATE users SET username = 'delilah_cooper', email = 'delilah.cooper@outlook.com' WHERE userId = 121;
UPDATE users SET username = 'tristan_richardson', email = 'tristan.richardson@gmail.com' WHERE userId = 122;
UPDATE users SET username = 'emilia_cox', email = 'emilia.cox@gmail.com' WHERE userId = 123;
UPDATE users SET username = 'silas_howard', email = 'silas.howard@hotmail.com' WHERE userId = 124;
UPDATE users SET username = 'ariana_ward', email = 'ariana.ward@outlook.com' WHERE userId = 125;
UPDATE users SET username = 'dean_torres', email = 'dean.torres@gmail.com' WHERE userId = 126;
UPDATE users SET username = 'valeria_peterson', email = 'valeria.peterson@gmail.com' WHERE userId = 127;
UPDATE users SET username = 'ezra_gray', email = 'ezra.gray@hotmail.com' WHERE userId = 128;
UPDATE users SET username = 'serenity_ramirez', email = 'serenity.ramirez@outlook.com' WHERE userId = 129;
UPDATE users SET username = 'bennett_james', email = 'bennett.james@gmail.com' WHERE userId = 130;
UPDATE users SET username = 'autumn_watson', email = 'autumn.watson@gmail.com' WHERE userId = 131;
UPDATE users SET username = 'rhett_brooks', email = 'rhett.brooks@hotmail.com' WHERE userId = 132;
UPDATE users SET username = 'june_kelly', email = 'june.kelly@outlook.com' WHERE userId = 133;
UPDATE users SET username = 'ryder_sanders', email = 'ryder.sanders@gmail.com' WHERE userId = 134;
UPDATE users SET username = 'piper_price', email = 'piper.price@gmail.com' WHERE userId = 135;
UPDATE users SET username = 'tucker_bennett', email = 'tucker.bennett@hotmail.com' WHERE userId = 136;
UPDATE users SET username = 'isla_wood', email = 'isla.wood@outlook.com' WHERE userId = 137;
UPDATE users SET username = 'maverick_ross', email = 'maverick.ross@gmail.com' WHERE userId = 138;
UPDATE users SET username = 'khloe_henderson', email = 'khloe.henderson@gmail.com' WHERE userId = 139;
UPDATE users SET username = 'cole_coleman', email = 'cole.coleman@hotmail.com' WHERE userId = 140;
UPDATE users SET username = 'jasmine_jenkins', email = 'jasmine.jenkins@outlook.com' WHERE userId = 141;
UPDATE users SET username = 'beau_perry', email = 'beau.perry@gmail.com' WHERE userId = 142;
UPDATE users SET username = 'kinsley_powell', email = 'kinsley.powell@gmail.com' WHERE userId = 143;
UPDATE users SET username = 'emmett_long', email = 'emmett.long@hotmail.com' WHERE userId = 144;
UPDATE users SET username = 'jade_patterson', email = 'jade.patterson@outlook.com' WHERE userId = 145;
UPDATE users SET username = 'nash_hughes', email = 'nash.hughes@gmail.com' WHERE userId = 146;
UPDATE users SET username = 'melody_reed', email = 'melody.reed@gmail.com' WHERE userId = 147;
UPDATE users SET username = 'sawyer_cox', email = 'sawyer.cox@hotmail.com' WHERE userId = 148;
UPDATE users SET username = 'morgan_howard', email = 'morgan.howard@outlook.com' WHERE userId = 149;
UPDATE users SET username = 'garrett_ward', email = 'garrett.ward@gmail.com' WHERE userId = 150;
UPDATE users SET username = 'blakely_torres', email = 'blakely.torres@gmail.com' WHERE userId = 151;
UPDATE users SET username = 'roman_peterson', email = 'roman.peterson@hotmail.com' WHERE userId = 152;
UPDATE users SET username = 'andrea_gray', email = 'andrea.gray@outlook.com' WHERE userId = 153;
UPDATE users SET username = 'brady_ramirez', email = 'brady.ramirez@gmail.com' WHERE userId = 154;
UPDATE users SET username = 'vanessa_james', email = 'vanessa.james@gmail.com' WHERE userId = 155;
UPDATE users SET username = 'finn_watson', email = 'finn.watson@hotmail.com' WHERE userId = 156;
UPDATE users SET username = 'presley_brooks', email = 'presley.brooks@outlook.com' WHERE userId = 157;
UPDATE users SET username = 'river_kelly', email = 'river.kelly@gmail.com' WHERE userId = 158;
UPDATE users SET username = 'kennedy_sanders', email = 'kennedy.sanders@gmail.com' WHERE userId = 159;
UPDATE users SET username = 'knox_price', email = 'knox.price@hotmail.com' WHERE userId = 160;
UPDATE users SET username = 'raelynn_bennett', email = 'raelynn.bennett@outlook.com' WHERE userId = 161;
UPDATE users SET username = 'dallas_wood', email = 'dallas.wood@gmail.com' WHERE userId = 162;
UPDATE users SET username = 'athena_ross', email = 'athena.ross@gmail.com' WHERE userId = 163;
UPDATE users SET username = 'harrison_henderson', email = 'harrison.henderson@hotmail.com' WHERE userId = 164;
UPDATE users SET username = 'eden_coleman', email = 'eden.coleman@outlook.com' WHERE userId = 165;
UPDATE users SET username = 'rowan_jenkins', email = 'rowan.jenkins@gmail.com' WHERE userId = 166;
UPDATE users SET username = 'adalynn_perry', email = 'adalynn.perry@gmail.com' WHERE userId = 167;
UPDATE users SET username = 'kingston_powell', email = 'kingston.powell@hotmail.com' WHERE userId = 168;
UPDATE users SET username = 'juliana_long', email = 'juliana.long@outlook.com' WHERE userId = 169;
UPDATE users SET username = 'felix_patterson', email = 'felix.patterson@gmail.com' WHERE userId = 170;
UPDATE users SET username = 'daisy_hughes', email = 'daisy.hughes@gmail.com' WHERE userId = 171;
UPDATE users SET username = 'jasper_reed', email = 'jasper.reed@hotmail.com' WHERE userId = 172;
UPDATE users SET username = 'eloise_cox', email = 'eloise.cox@outlook.com' WHERE userId = 173;
UPDATE users SET username = 'maxwell_howard', email = 'maxwell.howard@gmail.com' WHERE userId = 174;
UPDATE users SET username = 'nina_ward', email = 'nina.ward@gmail.com' WHERE userId = 175;
UPDATE users SET username = 'braxton_torres', email = 'braxton.torres@hotmail.com' WHERE userId = 176;
UPDATE users SET username = 'valentina_peterson', email = 'valentina.peterson@outlook.com' WHERE userId = 177;
UPDATE users SET username = 'emerson_gray', email = 'emerson.gray@gmail.com' WHERE userId = 178;
UPDATE users SET username = 'cecilia_ramirez', email = 'cecilia.ramirez@gmail.com' WHERE userId = 179;
UPDATE users SET username = 'cooper_james', email = 'cooper.james@hotmail.com' WHERE userId = 180;
UPDATE users SET username = 'rose_watson', email = 'rose.watson@outlook.com' WHERE userId = 181;
UPDATE users SET username = 'omar_brooks', email = 'omar.brooks@gmail.com' WHERE userId = 182;
UPDATE users SET username = 'alina_kelly', email = 'alina.kelly@gmail.com' WHERE userId = 183;
UPDATE users SET username = 'kyle_sanders', email = 'kyle.sanders@hotmail.com' WHERE userId = 184;
UPDATE users SET username = 'mariana_price', email = 'mariana.price@outlook.com' WHERE userId = 185;
UPDATE users SET username = 'preston_bennett', email = 'preston.bennett@gmail.com' WHERE userId = 186;
UPDATE users SET username = 'teagan_wood', email = 'teagan.wood@gmail.com' WHERE userId = 187;
UPDATE users SET username = 'joel_ross', email = 'joel.ross@hotmail.com' WHERE userId = 188;
UPDATE users SET username = 'gemma_henderson', email = 'gemma.henderson@outlook.com' WHERE userId = 189;
UPDATE users SET username = 'oscar_coleman', email = 'oscar.coleman@gmail.com' WHERE userId = 190;
UPDATE users SET username = 'freya_jenkins', email = 'freya.jenkins@gmail.com' WHERE userId = 191;
UPDATE users SET username = 'gage_perry', email = 'gage.perry@hotmail.com' WHERE userId = 192;
UPDATE users SET username = 'sloane_powell', email = 'sloane.powell@outlook.com' WHERE userId = 193;
UPDATE users SET username = 'zane_long', email = 'zane.long@gmail.com' WHERE userId = 194;
UPDATE users SET username = 'ophelia_patterson', email = 'ophelia.patterson@gmail.com' WHERE userId = 195;
UPDATE users SET username = 'beckett_hughes', email = 'beckett.hughes@hotmail.com' WHERE userId = 196;
UPDATE users SET username = 'gabriella_reed', email = 'gabriella.reed@outlook.com' WHERE userId = 197;
UPDATE users SET username = 'graham_cox', email = 'graham.cox@gmail.com' WHERE userId = 198;
UPDATE users SET username = 'lillian_howard', email = 'lillian.howard@gmail.com' WHERE userId = 199;
UPDATE users SET username = 'angel_ward', email = 'angel.ward@hotmail.com' WHERE userId = 200;

-- Users 201-250
UPDATE users SET username = 'poppy_torres', email = 'poppy.torres@outlook.com' WHERE userId = 201;
UPDATE users SET username = 'travis_peterson', email = 'travis.peterson@gmail.com' WHERE userId = 202;
UPDATE users SET username = 'lila_gray', email = 'lila.gray@gmail.com' WHERE userId = 203;
UPDATE users SET username = 'caden_ramirez', email = 'caden.ramirez@hotmail.com' WHERE userId = 204;
UPDATE users SET username = 'eliza_james', email = 'eliza.james@outlook.com' WHERE userId = 205;
UPDATE users SET username = 'tanner_watson', email = 'tanner.watson@gmail.com' WHERE userId = 206;
UPDATE users SET username = 'peyton_brooks', email = 'peyton.brooks@gmail.com' WHERE userId = 207;
UPDATE users SET username = 'xander_kelly', email = 'xander.kelly@hotmail.com' WHERE userId = 208;
UPDATE users SET username = 'quinn_sanders', email = 'quinn.sanders@outlook.com' WHERE userId = 209;
UPDATE users SET username = 'micah_price', email = 'micah.price@gmail.com' WHERE userId = 210;
UPDATE users SET username = 'iris_bennett', email = 'iris.bennett@gmail.com' WHERE userId = 211;
UPDATE users SET username = 'dante_wood', email = 'dante.wood@hotmail.com' WHERE userId = 212;
UPDATE users SET username = 'brielle_ross', email = 'brielle.ross@outlook.com' WHERE userId = 213;
UPDATE users SET username = 'archer_henderson', email = 'archer.henderson@gmail.com' WHERE userId = 214;
UPDATE users SET username = 'sienna_coleman', email = 'sienna.coleman@gmail.com' WHERE userId = 215;
UPDATE users SET username = 'kameron_jenkins', email = 'kameron.jenkins@hotmail.com' WHERE userId = 216;
UPDATE users SET username = 'juniper_perry', email = 'juniper.perry@outlook.com' WHERE userId = 217;
UPDATE users SET username = 'miguel_powell', email = 'miguel.powell@gmail.com' WHERE userId = 218;
UPDATE users SET username = 'margot_long', email = 'margot.long@gmail.com' WHERE userId = 219;
UPDATE users SET username = 'lance_patterson', email = 'lance.patterson@hotmail.com' WHERE userId = 220;
UPDATE users SET username = 'norah_hughes', email = 'norah.hughes@outlook.com' WHERE userId = 221;
UPDATE users SET username = 'phoenix_reed', email = 'phoenix.reed@gmail.com' WHERE userId = 222;
UPDATE users SET username = 'camila_cox', email = 'camila.cox@gmail.com' WHERE userId = 223;
UPDATE users SET username = 'paxton_howard', email = 'paxton.howard@hotmail.com' WHERE userId = 224;
UPDATE users SET username = 'esther_ward', email = 'esther.ward@outlook.com' WHERE userId = 225;
UPDATE users SET username = 'colin_torres', email = 'colin.torres@gmail.com' WHERE userId = 226;
UPDATE users SET username = 'mila_peterson', email = 'mila.peterson@gmail.com' WHERE userId = 227;
UPDATE users SET username = 'enzo_gray', email = 'enzo.gray@hotmail.com' WHERE userId = 228;
UPDATE users SET username = 'adeline_ramirez', email = 'adeline.ramirez@outlook.com' WHERE userId = 229;
UPDATE users SET username = 'sergio_james', email = 'sergio.james@gmail.com' WHERE userId = 230;
UPDATE users SET username = 'juniper_watson', email = 'juniper.watson@gmail.com' WHERE userId = 231;
UPDATE users SET username = 'andre_brooks', email = 'andre.brooks@hotmail.com' WHERE userId = 232;
UPDATE users SET username = 'sydney_kelly', email = 'sydney.kelly@outlook.com' WHERE userId = 233;
UPDATE users SET username = 'tucker_sanders', email = 'tucker.sanders@gmail.com' WHERE userId = 234;
UPDATE users SET username = 'paige_price', email = 'paige.price@gmail.com' WHERE userId = 235;
UPDATE users SET username = 'jonah_bennett', email = 'jonah.bennett@hotmail.com' WHERE userId = 236;
UPDATE users SET username = 'rosie_wood', email = 'rosie.wood@outlook.com' WHERE userId = 237;
UPDATE users SET username = 'elliott_ross', email = 'elliott.ross@gmail.com' WHERE userId = 238;
UPDATE users SET username = 'fiona_henderson', email = 'fiona.henderson@gmail.com' WHERE userId = 239;
UPDATE users SET username = 'donovan_coleman', email = 'donovan.coleman@hotmail.com' WHERE userId = 240;
UPDATE users SET username = 'maeve_jenkins', email = 'maeve.jenkins@outlook.com' WHERE userId = 241;
UPDATE users SET username = 'ellis_perry', email = 'ellis.perry@gmail.com' WHERE userId = 242;
UPDATE users SET username = 'diana_powell', email = 'diana.powell@gmail.com' WHERE userId = 243;
UPDATE users SET username = 'judah_long', email = 'judah.long@hotmail.com' WHERE userId = 244;
UPDATE users SET username = 'molly_patterson', email = 'molly.patterson@outlook.com' WHERE userId = 245;
UPDATE users SET username = 'kaiden_hughes', email = 'kaiden.hughes@gmail.com' WHERE userId = 246;
UPDATE users SET username = 'lucia_reed', email = 'lucia.reed@gmail.com' WHERE userId = 247;
UPDATE users SET username = 'troy_cox', email = 'troy.cox@hotmail.com' WHERE userId = 248;
UPDATE users SET username = 'vera_howard', email = 'vera.howard@outlook.com' WHERE userId = 249;
UPDATE users SET username = 'wesley_ward', email = 'wesley.ward@gmail.com' WHERE userId = 250;

-- For remaining users (251-674), use algorithmic pattern with diverse names
-- This creates realistic combinations using 50 first names and 20 last names
UPDATE users SET username = CONCAT(
    CASE (userId % 50)
        WHEN 0 THEN 'alex_'
        WHEN 1 THEN 'jordan_'
        WHEN 2 THEN 'taylor_'
        WHEN 3 THEN 'casey_'
        WHEN 4 THEN 'riley_'
        WHEN 5 THEN 'morgan_'
        WHEN 6 THEN 'parker_'
        WHEN 7 THEN 'quinn_'
        WHEN 8 THEN 'dakota_'
        WHEN 9 THEN 'avery_'
        WHEN 10 THEN 'cameron_'
        WHEN 11 THEN 'drew_'
        WHEN 12 THEN 'sage_'
        WHEN 13 THEN 'blake_'
        WHEN 14 THEN 'charlie_'
        WHEN 15 THEN 'skyler_'
        WHEN 16 THEN 'kendall_'
        WHEN 17 THEN 'reese_'
        WHEN 18 THEN 'bailey_'
        WHEN 19 THEN 'jamie_'
        WHEN 20 THEN 'rowan_'
        WHEN 21 THEN 'peyton_'
        WHEN 22 THEN 'finley_'
        WHEN 23 THEN 'phoenix_'
        WHEN 24 THEN 'river_'
        WHEN 25 THEN 'hayden_'
        WHEN 26 THEN 'max_'
        WHEN 27 THEN 'sam_'
        WHEN 28 THEN 'elliot_'
        WHEN 29 THEN 'leo_'
        WHEN 30 THEN 'milo_'
        WHEN 31 THEN 'kai_'
        WHEN 32 THEN 'finn_'
        WHEN 33 THEN 'jasper_'
        WHEN 34 THEN 'silas_'
        WHEN 35 THEN 'miles_'
        WHEN 36 THEN 'felix_'
        WHEN 37 THEN 'axel_'
        WHEN 38 THEN 'knox_'
        WHEN 39 THEN 'ezra_'
        WHEN 40 THEN 'luna_'
        WHEN 41 THEN 'nova_'
        WHEN 42 THEN 'ivy_'
        WHEN 43 THEN 'ruby_'
        WHEN 44 THEN 'hazel_'
        WHEN 45 THEN 'violet_'
        WHEN 46 THEN 'willow_'
        WHEN 47 THEN 'jade_'
        WHEN 48 THEN 'iris_'
        ELSE 'ellis_'
    END,
    CASE ((userId DIV 50) % 20)
        WHEN 0 THEN 'smith'
        WHEN 1 THEN 'johnson'
        WHEN 2 THEN 'williams'
        WHEN 3 THEN 'brown'
        WHEN 4 THEN 'jones'
        WHEN 5 THEN 'garcia'
        WHEN 6 THEN 'miller'
        WHEN 7 THEN 'davis'
        WHEN 8 THEN 'rodriguez'
        WHEN 9 THEN 'martinez'
        WHEN 10 THEN 'hernandez'
        WHEN 11 THEN 'lopez'
        WHEN 12 THEN 'gonzalez'
        WHEN 13 THEN 'wilson'
        WHEN 14 THEN 'anderson'
        WHEN 15 THEN 'thomas'
        WHEN 16 THEN 'taylor'
        WHEN 17 THEN 'moore'
        WHEN 18 THEN 'jackson'
        ELSE 'white'
    END
),
email = CONCAT(
    CASE (userId % 50)
        WHEN 0 THEN 'alex.'
        WHEN 1 THEN 'jordan.'
        WHEN 2 THEN 'taylor.'
        WHEN 3 THEN 'casey.'
        WHEN 4 THEN 'riley.'
        WHEN 5 THEN 'morgan.'
        WHEN 6 THEN 'parker.'
        WHEN 7 THEN 'quinn.'
        WHEN 8 THEN 'dakota.'
        WHEN 9 THEN 'avery.'
        WHEN 10 THEN 'cameron.'
        WHEN 11 THEN 'drew.'
        WHEN 12 THEN 'sage.'
        WHEN 13 THEN 'blake.'
        WHEN 14 THEN 'charlie.'
        WHEN 15 THEN 'skyler.'
        WHEN 16 THEN 'kendall.'
        WHEN 17 THEN 'reese.'
        WHEN 18 THEN 'bailey.'
        WHEN 19 THEN 'jamie.'
        WHEN 20 THEN 'rowan.'
        WHEN 21 THEN 'peyton.'
        WHEN 22 THEN 'finley.'
        WHEN 23 THEN 'phoenix.'
        WHEN 24 THEN 'river.'
        WHEN 25 THEN 'hayden.'
        WHEN 26 THEN 'max.'
        WHEN 27 THEN 'sam.'
        WHEN 28 THEN 'elliot.'
        WHEN 29 THEN 'leo.'
        WHEN 30 THEN 'milo.'
        WHEN 31 THEN 'kai.'
        WHEN 32 THEN 'finn.'
        WHEN 33 THEN 'jasper.'
        WHEN 34 THEN 'silas.'
        WHEN 35 THEN 'miles.'
        WHEN 36 THEN 'felix.'
        WHEN 37 THEN 'axel.'
        WHEN 38 THEN 'knox.'
        WHEN 39 THEN 'ezra.'
        WHEN 40 THEN 'luna.'
        WHEN 41 THEN 'nova.'
        WHEN 42 THEN 'ivy.'
        WHEN 43 THEN 'ruby.'
        WHEN 44 THEN 'hazel.'
        WHEN 45 THEN 'violet.'
        WHEN 46 THEN 'willow.'
        WHEN 47 THEN 'jade.'
        WHEN 48 THEN 'iris.'
        ELSE 'ellis.'
    END,
    CASE ((userId DIV 50) % 20)
        WHEN 0 THEN 'smith'
        WHEN 1 THEN 'johnson'
        WHEN 2 THEN 'williams'
        WHEN 3 THEN 'brown'
        WHEN 4 THEN 'jones'
        WHEN 5 THEN 'garcia'
        WHEN 6 THEN 'miller'
        WHEN 7 THEN 'davis'
        WHEN 8 THEN 'rodriguez'
        WHEN 9 THEN 'martinez'
        WHEN 10 THEN 'hernandez'
        WHEN 11 THEN 'lopez'
        WHEN 12 THEN 'gonzalez'
        WHEN 13 THEN 'wilson'
        WHEN 14 THEN 'anderson'
        WHEN 15 THEN 'thomas'
        WHEN 16 THEN 'taylor'
        WHEN 17 THEN 'moore'
        WHEN 18 THEN 'jackson'
        ELSE 'white'
    END,
    CASE (userId % 3)
        WHEN 0 THEN '@gmail.com'
        WHEN 1 THEN '@hotmail.com'
        ELSE '@outlook.com'
    END
)
WHERE userId > 250;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Show statistics
SELECT 
    COUNT(*) as total_users,
    COUNT(DISTINCT username) as unique_usernames,
    COUNT(DISTINCT email) as unique_emails,
    SUM(CASE WHEN username LIKE 'user_%' THEN 1 ELSE 0 END) as generic_names,
    SUM(CASE WHEN username IS NOT NULL THEN 1 ELSE 0 END) as users_with_names,
    SUM(CASE WHEN email IS NOT NULL THEN 1 ELSE 0 END) as users_with_emails
FROM users;

-- Show sample of updated users across the range
SELECT userId, username, email, role 
FROM users 
WHERE userId IN (1, 2, 50, 100, 150, 200, 250, 300, 400, 500, 600, 674)
ORDER BY userId;

-- Show first 30 users
SELECT userId, username, email, role, created_at 
FROM users 
ORDER BY userId 
LIMIT 30;
