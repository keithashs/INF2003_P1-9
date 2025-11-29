-- ============================================================================
-- UPDATE ALL USERS WITH REALISTIC NAMES AND EMAILS
-- This script adds realistic names and emails for all 674 users
-- Mix of male and female names from various backgrounds
-- Email domains: @gmail.com, @hotmail.com, @outlook.com
-- ============================================================================

USE movies_db;

-- Users 3-22 (original set)
UPDATE USERS SET username = 'emma_wilson', email = 'emma.wilson@gmail.com' WHERE userId = 3;
UPDATE USERS SET username = 'james_chen', email = 'james.chen@hotmail.com' WHERE userId = 4;
UPDATE USERS SET username = 'sophia_garcia', email = 'sophia.garcia@outlook.com' WHERE userId = 5;
UPDATE USERS SET username = 'liam_patel', email = 'liam.patel@gmail.com' WHERE userId = 6;
UPDATE USERS SET username = 'olivia_kim', email = 'olivia.kim@gmail.com' WHERE userId = 7;
UPDATE USERS SET username = 'noah_rodriguez', email = 'noah.rodriguez@hotmail.com' WHERE userId = 8;
UPDATE USERS SET username = 'ava_nguyen', email = 'ava.nguyen@outlook.com' WHERE userId = 9;
UPDATE USERS SET username = 'ethan_singh', email = 'ethan.singh@gmail.com' WHERE userId = 10;
UPDATE USERS SET username = 'isabella_lee', email = 'isabella.lee@gmail.com' WHERE userId = 11;
UPDATE USERS SET username = 'mason_brown', email = 'mason.brown@hotmail.com' WHERE userId = 12;
UPDATE USERS SET username = 'mia_davis', email = 'mia.davis@outlook.com' WHERE userId = 13;
UPDATE USERS SET username = 'lucas_martinez', email = 'lucas.martinez@gmail.com' WHERE userId = 14;
UPDATE USERS SET username = 'charlotte_taylor', email = 'charlotte.taylor@gmail.com' WHERE userId = 15;
UPDATE USERS SET username = 'aiden_thomas', email = 'aiden.thomas@hotmail.com' WHERE userId = 16;
UPDATE USERS SET username = 'amelia_white', email = 'amelia.white@outlook.com' WHERE userId = 17;
UPDATE USERS SET username = 'jackson_harris', email = 'jackson.harris@gmail.com' WHERE userId = 18;
UPDATE USERS SET username = 'harper_clark', email = 'harper.clark@gmail.com' WHERE userId = 19;
UPDATE USERS SET username = 'sebastian_lewis', email = 'sebastian.lewis@hotmail.com' WHERE userId = 20;
UPDATE USERS SET username = 'evelyn_walker', email = 'evelyn.walker@outlook.com' WHERE userId = 21;
UPDATE USERS SET username = 'jack_hall', email = 'jack.hall@gmail.com' WHERE userId = 22;

-- Users 23-100
UPDATE USERS SET username = 'maya_johnson', email = 'maya.johnson@gmail.com' WHERE userId = 23;
UPDATE USERS SET username = 'daniel_wong', email = 'daniel.wong@hotmail.com' WHERE userId = 24;
UPDATE USERS SET username = 'sarah_anderson', email = 'sarah.anderson@outlook.com' WHERE userId = 25;
UPDATE USERS SET username = 'ryan_kumar', email = 'ryan.kumar@gmail.com' WHERE userId = 26;
UPDATE USERS SET username = 'grace_martin', email = 'grace.martin@gmail.com' WHERE userId = 27;
UPDATE USERS SET username = 'tyler_brooks', email = 'tyler.brooks@hotmail.com' WHERE userId = 28;
UPDATE USERS SET username = 'hannah_cooper', email = 'hannah.cooper@outlook.com' WHERE userId = 29;
UPDATE USERS SET username = 'alex_rivera', email = 'alex.rivera@gmail.com' WHERE userId = 30;
UPDATE USERS SET username = 'lily_peterson', email = 'lily.peterson@gmail.com' WHERE userId = 31;
UPDATE USERS SET username = 'marcus_james', email = 'marcus.james@hotmail.com' WHERE userId = 32;
UPDATE USERS SET username = 'chloe_bailey', email = 'chloe.bailey@outlook.com' WHERE userId = 33;
UPDATE USERS SET username = 'jordan_mills', email = 'jordan.mills@gmail.com' WHERE userId = 34;
UPDATE USERS SET username = 'zoe_collins', email = 'zoe.collins@gmail.com' WHERE userId = 35;
UPDATE USERS SET username = 'nathan_gray', email = 'nathan.gray@hotmail.com' WHERE userId = 36;
UPDATE USERS SET username = 'emily_foster', email = 'emily.foster@outlook.com' WHERE userId = 37;
UPDATE USERS SET username = 'dylan_hughes', email = 'dylan.hughes@gmail.com' WHERE userId = 38;
UPDATE USERS SET username = 'rachel_coleman', email = 'rachel.coleman@gmail.com' WHERE userId = 39;
UPDATE USERS SET username = 'kevin_jenkins', email = 'kevin.jenkins@hotmail.com' WHERE userId = 40;
UPDATE USERS SET username = 'anna_perry', email = 'anna.perry@outlook.com' WHERE userId = 41;
UPDATE USERS SET username = 'brandon_powell', email = 'brandon.powell@gmail.com' WHERE userId = 42;
UPDATE USERS SET username = 'natalie_long', email = 'natalie.long@gmail.com' WHERE userId = 43;
UPDATE USERS SET username = 'justin_patterson', email = 'justin.patterson@hotmail.com' WHERE userId = 44;
UPDATE USERS SET username = 'victoria_hughes', email = 'victoria.hughes@outlook.com' WHERE userId = 45;
UPDATE USERS SET username = 'austin_reed', email = 'austin.reed@gmail.com' WHERE userId = 46;
UPDATE USERS SET username = 'madison_cox', email = 'madison.cox@gmail.com' WHERE userId = 47;
UPDATE USERS SET username = 'cameron_howard', email = 'cameron.howard@hotmail.com' WHERE userId = 48;
UPDATE USERS SET username = 'julia_ward', email = 'julia.ward@outlook.com' WHERE userId = 49;
UPDATE USERS SET username = 'connor_torres', email = 'connor.torres@gmail.com' WHERE userId = 50;
UPDATE USERS SET username = 'abigail_peterson', email = 'abigail.peterson@gmail.com' WHERE userId = 51;
UPDATE USERS SET username = 'adam_gray', email = 'adam.gray@hotmail.com' WHERE userId = 52;
UPDATE USERS SET username = 'samantha_ramirez', email = 'samantha.ramirez@outlook.com' WHERE userId = 53;
UPDATE USERS SET username = 'jason_james', email = 'jason.james@gmail.com' WHERE userId = 54;
UPDATE USERS SET username = 'bella_watson', email = 'bella.watson@gmail.com' WHERE userId = 55;
UPDATE USERS SET username = 'nicholas_brooks', email = 'nicholas.brooks@hotmail.com' WHERE userId = 56;
UPDATE USERS SET username = 'sophie_kelly', email = 'sophie.kelly@outlook.com' WHERE userId = 57;
UPDATE USERS SET username = 'zachary_sanders', email = 'zachary.sanders@gmail.com' WHERE userId = 58;
UPDATE USERS SET username = 'claire_price', email = 'claire.price@gmail.com' WHERE userId = 59;
UPDATE USERS SET username = 'elijah_bennett', email = 'elijah.bennett@hotmail.com' WHERE userId = 60;
UPDATE USERS SET username = 'lucy_wood', email = 'lucy.wood@outlook.com' WHERE userId = 61;
UPDATE USERS SET username = 'henry_ross', email = 'henry.ross@gmail.com' WHERE userId = 62;
UPDATE USERS SET username = 'stella_henderson', email = 'stella.henderson@gmail.com' WHERE userId = 63;
UPDATE USERS SET username = 'oliver_coleman', email = 'oliver.coleman@hotmail.com' WHERE userId = 64;
UPDATE USERS SET username = 'aurora_jenkins', email = 'aurora.jenkins@outlook.com' WHERE userId = 65;
UPDATE USERS SET username = 'leo_perry', email = 'leo.perry@gmail.com' WHERE userId = 66;
UPDATE USERS SET username = 'hazel_powell', email = 'hazel.powell@gmail.com' WHERE userId = 67;
UPDATE USERS SET username = 'carter_long', email = 'carter.long@hotmail.com' WHERE userId = 68;
UPDATE USERS SET username = 'violet_patterson', email = 'violet.patterson@outlook.com' WHERE userId = 69;
UPDATE USERS SET username = 'wyatt_hughes', email = 'wyatt.hughes@gmail.com' WHERE userId = 70;
UPDATE USERS SET username = 'nora_reed', email = 'nora.reed@gmail.com' WHERE userId = 71;
UPDATE USERS SET username = 'owen_cox', email = 'owen.cox@hotmail.com' WHERE userId = 72;
UPDATE USERS SET username = 'ellie_howard', email = 'ellie.howard@outlook.com' WHERE userId = 73;
UPDATE USERS SET username = 'gabriel_ward', email = 'gabriel.ward@gmail.com' WHERE userId = 74;
UPDATE USERS SET username = 'aria_torres', email = 'aria.torres@gmail.com' WHERE userId = 75;
UPDATE USERS SET username = 'miles_peterson', email = 'miles.peterson@hotmail.com' WHERE userId = 76;
UPDATE USERS SET username = 'scarlett_gray', email = 'scarlett.gray@outlook.com' WHERE userId = 77;
UPDATE USERS SET username = 'logan_ramirez', email = 'logan.ramirez@gmail.com' WHERE userId = 78;
UPDATE USERS SET username = 'penelope_james', email = 'penelope.james@gmail.com' WHERE userId = 79;
UPDATE USERS SET username = 'eli_watson', email = 'eli.watson@hotmail.com' WHERE userId = 80;
UPDATE USERS SET username = 'layla_brooks', email = 'layla.brooks@outlook.com' WHERE userId = 81;
UPDATE USERS SET username = 'isaac_kelly', email = 'isaac.kelly@gmail.com' WHERE userId = 82;
UPDATE USERS SET username = 'riley_sanders', email = 'riley.sanders@gmail.com' WHERE userId = 83;
UPDATE USERS SET username = 'mateo_price', email = 'mateo.price@hotmail.com' WHERE userId = 84;
UPDATE USERS SET username = 'zoey_bennett', email = 'zoey.bennett@outlook.com' WHERE userId = 85;
UPDATE USERS SET username = 'lincoln_wood', email = 'lincoln.wood@gmail.com' WHERE userId = 86;
UPDATE USERS SET username = 'nova_ross', email = 'nova.ross@gmail.com' WHERE userId = 87;
UPDATE USERS SET username = 'theo_henderson', email = 'theo.henderson@hotmail.com' WHERE userId = 88;
UPDATE USERS SET username = 'elena_coleman', email = 'elena.coleman@outlook.com' WHERE userId = 89;
UPDATE USERS SET username = 'asher_jenkins', email = 'asher.jenkins@gmail.com' WHERE userId = 90;
UPDATE USERS SET username = 'maya_perry', email = 'maya.perry@gmail.com' WHERE userId = 91;
UPDATE USERS SET username = 'levi_powell', email = 'levi.powell@hotmail.com' WHERE userId = 92;
UPDATE USERS SET username = 'willow_long', email = 'willow.long@outlook.com' WHERE userId = 93;
UPDATE USERS SET username = 'hunter_patterson', email = 'hunter.patterson@gmail.com' WHERE userId = 94;
UPDATE USERS SET username = 'ivy_hughes', email = 'ivy.hughes@gmail.com' WHERE userId = 95;
UPDATE USERS SET username = 'landon_reed', email = 'landon.reed@hotmail.com' WHERE userId = 96;
UPDATE USERS SET username = 'ruby_cox', email = 'ruby.cox@outlook.com' WHERE userId = 97;
UPDATE USERS SET username = 'colton_howard', email = 'colton.howard@gmail.com' WHERE userId = 98;
UPDATE USERS SET username = 'paisley_ward', email = 'paisley.ward@gmail.com' WHERE userId = 99;
UPDATE USERS SET username = 'parker_torres', email = 'parker.torres@hotmail.com' WHERE userId = 100;

-- Users 101-200
UPDATE USERS SET username = 'skylar_anderson', email = 'skylar.anderson@outlook.com' WHERE userId = 101;
UPDATE USERS SET username = 'chase_mitchell', email = 'chase.mitchell@gmail.com' WHERE userId = 102;
UPDATE USERS SET username = 'brooklyn_carter', email = 'brooklyn.carter@gmail.com' WHERE userId = 103;
UPDATE USERS SET username = 'adrian_roberts', email = 'adrian.roberts@hotmail.com' WHERE userId = 104;
UPDATE USERS SET username = 'savannah_turner', email = 'savannah.turner@outlook.com' WHERE userId = 105;
UPDATE USERS SET username = 'blake_phillips', email = 'blake.phillips@gmail.com' WHERE userId = 106;
UPDATE USERS SET username = 'natalia_campbell', email = 'natalia.campbell@gmail.com' WHERE userId = 107;
UPDATE USERS SET username = 'jaxon_evans', email = 'jaxon.evans@hotmail.com' WHERE userId = 108;
UPDATE USERS SET username = 'luna_edwards', email = 'luna.edwards@outlook.com' WHERE userId = 109;
UPDATE USERS SET username = 'carson_collins', email = 'carson.collins@gmail.com' WHERE userId = 110;
UPDATE USERS SET username = 'alice_stewart', email = 'alice.stewart@gmail.com' WHERE userId = 111;
UPDATE USERS SET username = 'hudson_sanchez', email = 'hudson.sanchez@hotmail.com' WHERE userId = 112;
UPDATE USERS SET username = 'clara_morris', email = 'clara.morris@outlook.com' WHERE userId = 113;
UPDATE USERS SET username = 'easton_rogers', email = 'easton.rogers@gmail.com' WHERE userId = 114;
UPDATE USERS SET username = 'audrey_cook', email = 'audrey.cook@gmail.com' WHERE userId = 115;
UPDATE USERS SET username = 'axel_morgan', email = 'axel.morgan@hotmail.com' WHERE userId = 116;
UPDATE USERS SET username = 'aaliyah_bell', email = 'aaliyah.bell@outlook.com' WHERE userId = 117;
UPDATE USERS SET username = 'evan_murphy', email = 'evan.murphy@gmail.com' WHERE userId = 118;
UPDATE USERS SET username = 'lydia_bailey', email = 'lydia.bailey@gmail.com' WHERE userId = 119;
UPDATE USERS SET username = 'xavier_rivera', email = 'xavier.rivera@hotmail.com' WHERE userId = 120;
UPDATE USERS SET username = 'delilah_cooper', email = 'delilah.cooper@outlook.com' WHERE userId = 121;
UPDATE USERS SET username = 'tristan_richardson', email = 'tristan.richardson@gmail.com' WHERE userId = 122;
UPDATE USERS SET username = 'emilia_cox', email = 'emilia.cox@gmail.com' WHERE userId = 123;
UPDATE USERS SET username = 'silas_howard', email = 'silas.howard@hotmail.com' WHERE userId = 124;
UPDATE USERS SET username = 'ariana_ward', email = 'ariana.ward@outlook.com' WHERE userId = 125;
UPDATE USERS SET username = 'dean_torres', email = 'dean.torres@gmail.com' WHERE userId = 126;
UPDATE USERS SET username = 'valeria_peterson', email = 'valeria.peterson@gmail.com' WHERE userId = 127;
UPDATE USERS SET username = 'ezra_gray', email = 'ezra.gray@hotmail.com' WHERE userId = 128;
UPDATE USERS SET username = 'serenity_ramirez', email = 'serenity.ramirez@outlook.com' WHERE userId = 129;
UPDATE USERS SET username = 'bennett_james', email = 'bennett.james@gmail.com' WHERE userId = 130;
UPDATE USERS SET username = 'autumn_watson', email = 'autumn.watson@gmail.com' WHERE userId = 131;
UPDATE USERS SET username = 'rhett_brooks', email = 'rhett.brooks@hotmail.com' WHERE userId = 132;
UPDATE USERS SET username = 'june_kelly', email = 'june.kelly@outlook.com' WHERE userId = 133;
UPDATE USERS SET username = 'ryder_sanders', email = 'ryder.sanders@gmail.com' WHERE userId = 134;
UPDATE USERS SET username = 'piper_price', email = 'piper.price@gmail.com' WHERE userId = 135;
UPDATE USERS SET username = 'tucker_bennett', email = 'tucker.bennett@hotmail.com' WHERE userId = 136;
UPDATE USERS SET username = 'isla_wood', email = 'isla.wood@outlook.com' WHERE userId = 137;
UPDATE USERS SET username = 'maverick_ross', email = 'maverick.ross@gmail.com' WHERE userId = 138;
UPDATE USERS SET username = 'khloe_henderson', email = 'khloe.henderson@gmail.com' WHERE userId = 139;
UPDATE USERS SET username = 'cole_coleman', email = 'cole.coleman@hotmail.com' WHERE userId = 140;
UPDATE USERS SET username = 'jasmine_jenkins', email = 'jasmine.jenkins@outlook.com' WHERE userId = 141;
UPDATE USERS SET username = 'beau_perry', email = 'beau.perry@gmail.com' WHERE userId = 142;
UPDATE USERS SET username = 'kinsley_powell', email = 'kinsley.powell@gmail.com' WHERE userId = 143;
UPDATE USERS SET username = 'emmett_long', email = 'emmett.long@hotmail.com' WHERE userId = 144;
UPDATE USERS SET username = 'jade_patterson', email = 'jade.patterson@outlook.com' WHERE userId = 145;
UPDATE USERS SET username = 'nash_hughes', email = 'nash.hughes@gmail.com' WHERE userId = 146;
UPDATE USERS SET username = 'melody_reed', email = 'melody.reed@gmail.com' WHERE userId = 147;
UPDATE USERS SET username = 'sawyer_cox', email = 'sawyer.cox@hotmail.com' WHERE userId = 148;
UPDATE USERS SET username = 'morgan_howard', email = 'morgan.howard@outlook.com' WHERE userId = 149;
UPDATE USERS SET username = 'garrett_ward', email = 'garrett.ward@gmail.com' WHERE userId = 150;
UPDATE USERS SET username = 'blakely_torres', email = 'blakely.torres@gmail.com' WHERE userId = 151;
UPDATE USERS SET username = 'roman_peterson', email = 'roman.peterson@hotmail.com' WHERE userId = 152;
UPDATE USERS SET username = 'andrea_gray', email = 'andrea.gray@outlook.com' WHERE userId = 153;
UPDATE USERS SET username = 'brady_ramirez', email = 'brady.ramirez@gmail.com' WHERE userId = 154;
UPDATE USERS SET username = 'vanessa_james', email = 'vanessa.james@gmail.com' WHERE userId = 155;
UPDATE USERS SET username = 'finn_watson', email = 'finn.watson@hotmail.com' WHERE userId = 156;
UPDATE USERS SET username = 'presley_brooks', email = 'presley.brooks@outlook.com' WHERE userId = 157;
UPDATE USERS SET username = 'river_kelly', email = 'river.kelly@gmail.com' WHERE userId = 158;
UPDATE USERS SET username = 'kennedy_sanders', email = 'kennedy.sanders@gmail.com' WHERE userId = 159;
UPDATE USERS SET username = 'knox_price', email = 'knox.price@hotmail.com' WHERE userId = 160;
UPDATE USERS SET username = 'raelynn_bennett', email = 'raelynn.bennett@outlook.com' WHERE userId = 161;
UPDATE USERS SET username = 'dallas_wood', email = 'dallas.wood@gmail.com' WHERE userId = 162;
UPDATE USERS SET username = 'athena_ross', email = 'athena.ross@gmail.com' WHERE userId = 163;
UPDATE USERS SET username = 'harrison_henderson', email = 'harrison.henderson@hotmail.com' WHERE userId = 164;
UPDATE USERS SET username = 'eden_coleman', email = 'eden.coleman@outlook.com' WHERE userId = 165;
UPDATE USERS SET username = 'rowan_jenkins', email = 'rowan.jenkins@gmail.com' WHERE userId = 166;
UPDATE USERS SET username = 'adalynn_perry', email = 'adalynn.perry@gmail.com' WHERE userId = 167;
UPDATE USERS SET username = 'kingston_powell', email = 'kingston.powell@hotmail.com' WHERE userId = 168;
UPDATE USERS SET username = 'juliana_long', email = 'juliana.long@outlook.com' WHERE userId = 169;
UPDATE USERS SET username = 'felix_patterson', email = 'felix.patterson@gmail.com' WHERE userId = 170;
UPDATE USERS SET username = 'daisy_hughes', email = 'daisy.hughes@gmail.com' WHERE userId = 171;
UPDATE USERS SET username = 'jasper_reed', email = 'jasper.reed@hotmail.com' WHERE userId = 172;
UPDATE USERS SET username = 'eloise_cox', email = 'eloise.cox@outlook.com' WHERE userId = 173;
UPDATE USERS SET username = 'maxwell_howard', email = 'maxwell.howard@gmail.com' WHERE userId = 174;
UPDATE USERS SET username = 'nina_ward', email = 'nina.ward@gmail.com' WHERE userId = 175;
UPDATE USERS SET username = 'braxton_torres', email = 'braxton.torres@hotmail.com' WHERE userId = 176;
UPDATE USERS SET username = 'valentina_peterson', email = 'valentina.peterson@outlook.com' WHERE userId = 177;
UPDATE USERS SET username = 'emerson_gray', email = 'emerson.gray@gmail.com' WHERE userId = 178;
UPDATE USERS SET username = 'cecilia_ramirez', email = 'cecilia.ramirez@gmail.com' WHERE userId = 179;
UPDATE USERS SET username = 'cooper_james', email = 'cooper.james@hotmail.com' WHERE userId = 180;
UPDATE USERS SET username = 'rose_watson', email = 'rose.watson@outlook.com' WHERE userId = 181;
UPDATE USERS SET username = 'omar_brooks', email = 'omar.brooks@gmail.com' WHERE userId = 182;
UPDATE USERS SET username = 'alina_kelly', email = 'alina.kelly@gmail.com' WHERE userId = 183;
UPDATE USERS SET username = 'kyle_sanders', email = 'kyle.sanders@hotmail.com' WHERE userId = 184;
UPDATE USERS SET username = 'mariana_price', email = 'mariana.price@outlook.com' WHERE userId = 185;
UPDATE USERS SET username = 'preston_bennett', email = 'preston.bennett@gmail.com' WHERE userId = 186;
UPDATE USERS SET username = 'teagan_wood', email = 'teagan.wood@gmail.com' WHERE userId = 187;
UPDATE USERS SET username = 'joel_ross', email = 'joel.ross@hotmail.com' WHERE userId = 188;
UPDATE USERS SET username = 'gemma_henderson', email = 'gemma.henderson@outlook.com' WHERE userId = 189;
UPDATE USERS SET username = 'oscar_coleman', email = 'oscar.coleman@gmail.com' WHERE userId = 190;
UPDATE USERS SET username = 'freya_jenkins', email = 'freya.jenkins@gmail.com' WHERE userId = 191;
UPDATE USERS SET username = 'gage_perry', email = 'gage.perry@hotmail.com' WHERE userId = 192;
UPDATE USERS SET username = 'sloane_powell', email = 'sloane.powell@outlook.com' WHERE userId = 193;
UPDATE USERS SET username = 'zane_long', email = 'zane.long@gmail.com' WHERE userId = 194;
UPDATE USERS SET username = 'ophelia_patterson', email = 'ophelia.patterson@gmail.com' WHERE userId = 195;
UPDATE USERS SET username = 'beckett_hughes', email = 'beckett.hughes@hotmail.com' WHERE userId = 196;
UPDATE USERS SET username = 'gabriella_reed', email = 'gabriella.reed@outlook.com' WHERE userId = 197;
UPDATE USERS SET username = 'graham_cox', email = 'graham.cox@gmail.com' WHERE userId = 198;
UPDATE USERS SET username = 'lillian_howard', email = 'lillian.howard@gmail.com' WHERE userId = 199;
UPDATE USERS SET username = 'angel_ward', email = 'angel.ward@hotmail.com' WHERE userId = 200;

-- Users 201-250
UPDATE USERS SET username = 'poppy_torres', email = 'poppy.torres@outlook.com' WHERE userId = 201;
UPDATE USERS SET username = 'travis_peterson', email = 'travis.peterson@gmail.com' WHERE userId = 202;
UPDATE USERS SET username = 'lila_gray', email = 'lila.gray@gmail.com' WHERE userId = 203;
UPDATE USERS SET username = 'caden_ramirez', email = 'caden.ramirez@hotmail.com' WHERE userId = 204;
UPDATE USERS SET username = 'eliza_james', email = 'eliza.james@outlook.com' WHERE userId = 205;
UPDATE USERS SET username = 'tanner_watson', email = 'tanner.watson@gmail.com' WHERE userId = 206;
UPDATE USERS SET username = 'peyton_brooks', email = 'peyton.brooks@gmail.com' WHERE userId = 207;
UPDATE USERS SET username = 'xander_kelly', email = 'xander.kelly@hotmail.com' WHERE userId = 208;
UPDATE USERS SET username = 'quinn_sanders', email = 'quinn.sanders@outlook.com' WHERE userId = 209;
UPDATE USERS SET username = 'micah_price', email = 'micah.price@gmail.com' WHERE userId = 210;
UPDATE USERS SET username = 'iris_bennett', email = 'iris.bennett@gmail.com' WHERE userId = 211;
UPDATE USERS SET username = 'dante_wood', email = 'dante.wood@hotmail.com' WHERE userId = 212;
UPDATE USERS SET username = 'brielle_ross', email = 'brielle.ross@outlook.com' WHERE userId = 213;
UPDATE USERS SET username = 'archer_henderson', email = 'archer.henderson@gmail.com' WHERE userId = 214;
UPDATE USERS SET username = 'sienna_coleman', email = 'sienna.coleman@gmail.com' WHERE userId = 215;
UPDATE USERS SET username = 'kameron_jenkins', email = 'kameron.jenkins@hotmail.com' WHERE userId = 216;
UPDATE USERS SET username = 'juniper_perry', email = 'juniper.perry@outlook.com' WHERE userId = 217;
UPDATE USERS SET username = 'miguel_powell', email = 'miguel.powell@gmail.com' WHERE userId = 218;
UPDATE USERS SET username = 'margot_long', email = 'margot.long@gmail.com' WHERE userId = 219;
UPDATE USERS SET username = 'lance_patterson', email = 'lance.patterson@hotmail.com' WHERE userId = 220;
UPDATE USERS SET username = 'norah_hughes', email = 'norah.hughes@outlook.com' WHERE userId = 221;
UPDATE USERS SET username = 'phoenix_reed', email = 'phoenix.reed@gmail.com' WHERE userId = 222;
UPDATE USERS SET username = 'camila_cox', email = 'camila.cox@gmail.com' WHERE userId = 223;
UPDATE USERS SET username = 'paxton_howard', email = 'paxton.howard@hotmail.com' WHERE userId = 224;
UPDATE USERS SET username = 'esther_ward', email = 'esther.ward@outlook.com' WHERE userId = 225;
UPDATE USERS SET username = 'colin_torres', email = 'colin.torres@gmail.com' WHERE userId = 226;
UPDATE USERS SET username = 'mila_peterson', email = 'mila.peterson@gmail.com' WHERE userId = 227;
UPDATE USERS SET username = 'enzo_gray', email = 'enzo.gray@hotmail.com' WHERE userId = 228;
UPDATE USERS SET username = 'adeline_ramirez', email = 'adeline.ramirez@outlook.com' WHERE userId = 229;
UPDATE USERS SET username = 'sergio_james', email = 'sergio.james@gmail.com' WHERE userId = 230;
UPDATE USERS SET username = 'juniper_watson', email = 'juniper.watson@gmail.com' WHERE userId = 231;
UPDATE USERS SET username = 'andre_brooks', email = 'andre.brooks@hotmail.com' WHERE userId = 232;
UPDATE USERS SET username = 'sydney_kelly', email = 'sydney.kelly@outlook.com' WHERE userId = 233;
UPDATE USERS SET username = 'tucker_sanders', email = 'tucker.sanders@gmail.com' WHERE userId = 234;
UPDATE USERS SET username = 'paige_price', email = 'paige.price@gmail.com' WHERE userId = 235;
UPDATE USERS SET username = 'jonah_bennett', email = 'jonah.bennett@hotmail.com' WHERE userId = 236;
UPDATE USERS SET username = 'rosie_wood', email = 'rosie.wood@outlook.com' WHERE userId = 237;
UPDATE USERS SET username = 'elliott_ross', email = 'elliott.ross@gmail.com' WHERE userId = 238;
UPDATE USERS SET username = 'fiona_henderson', email = 'fiona.henderson@gmail.com' WHERE userId = 239;
UPDATE USERS SET username = 'donovan_coleman', email = 'donovan.coleman@hotmail.com' WHERE userId = 240;
UPDATE USERS SET username = 'maeve_jenkins', email = 'maeve.jenkins@outlook.com' WHERE userId = 241;
UPDATE USERS SET username = 'ellis_perry', email = 'ellis.perry@gmail.com' WHERE userId = 242;
UPDATE USERS SET username = 'diana_powell', email = 'diana.powell@gmail.com' WHERE userId = 243;
UPDATE USERS SET username = 'judah_long', email = 'judah.long@hotmail.com' WHERE userId = 244;
UPDATE USERS SET username = 'molly_patterson', email = 'molly.patterson@outlook.com' WHERE userId = 245;
UPDATE USERS SET username = 'kaiden_hughes', email = 'kaiden.hughes@gmail.com' WHERE userId = 246;
UPDATE USERS SET username = 'lucia_reed', email = 'lucia.reed@gmail.com' WHERE userId = 247;
UPDATE USERS SET username = 'troy_cox', email = 'troy.cox@hotmail.com' WHERE userId = 248;
UPDATE USERS SET username = 'vera_howard', email = 'vera.howard@outlook.com' WHERE userId = 249;
UPDATE USERS SET username = 'wesley_ward', email = 'wesley.ward@gmail.com' WHERE userId = 250;

-- For remaining users (251-674), use algorithmic pattern with diverse names
-- This creates realistic combinations using 50 first names and 20 last names
UPDATE USERS SET username = CONCAT(
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
