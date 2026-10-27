# System KAROLINA
Napad na it firemni system, ktery pomaha ridit dopravni firmu. 

## Aktualni stav
1) Dispecer najde/objedna/domluvi prepravu. Zapise si k sobe novou objednavku

2) Ridic pri kazde preprave nashromazdi nekolik dokumentu 
    - Objednavka o preprave
    - Vazenka pri nakladce
    - Vazenka pri vykladce
    - Dokument o vycisteni korby pred nakladkou
    - A dalsi dokumenty...

3) Ridic vsechny nashromazdene dokumenty preda v kancelari Karoline. 

## Co dela Karolina ted:
- zpracovava, tridi dokumenty, ktere prinesou ridici do kancelare z nakladek/vykladek
- pokud nejaky dokument chybi nebo je chybny, musi je dodat upravit
- objednavku s informacemi zapise do ucetniho systemu POHODA a vystavi fakturu
- fakturu na zaplaceni posle emailem odberateli, kdo si prepravu objednal
- po zaplaceni sparuje transakci s objednavkou v systtemu POHODA

**Aktualni situace je nasledujici:** Karolina odchazi na materskou a nema kdo by to po ni prevzal. Napadl me tedy napad, zda by toto neslo nahradit nejakym pokrocilym it systemem s pouziti AI.

## Myslenka IT Systemu KAROLINA
Napadlo me, ze bych navrhl komplexni IT system ktery by cely tento proces razantne zjednodusil
- dispecer zada novou prepravu do systemu
- preprava je zadana ridici
- ridic vidi na jake preprave momentalne pracuje
- ridic muze elektronicky (sam) vyplnit a dodat vsechny dokumenty ktere pri prerave nashromazdi
- dispecer vse vidi a muze dokumenty kontrolovat/editovat
- pri splneni prepravy system vygeneruje fakturu skrz system POHODA a odesle emailem odberatelovi
- system je napojeny na vypis plateb z banky a automaticky paruje platby s fakturami

Napadlo me, ze by to cele mohlo fungovat i jako ai workflow langchain asistant. Umim si predstavit, ze by se to mohlo napojit i na nejaky MCP server.
