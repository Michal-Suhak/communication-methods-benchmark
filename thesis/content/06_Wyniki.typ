#import "../utils.typ": todo, silentheading, flex-caption, placeholder

= Wyniki badań <wyniki>

Rozdział szósty zawiera prezentację i analizę wyników przeprowadzonych eksperymentów
pomiarowych. Wyniki przedstawiono w formie tabel zbiorczych oraz wykresów porównawczych, a
następnie omówiono zarówno w ujęciu ilościowym, jak i jakościowym, z uwzględnieniem
istotności statystycznej zaobserwowanych różnic.

Prezentowane dane pochodzą z pojedynczej, spójnej kampanii pomiarowej obejmującej wszystkie
pięć metod komunikacji oraz wszystkie zdefiniowane scenariusze; łącznie obsłużono ponad
5,2 mln żądań przy globalnym odsetku błędów wynoszącym 0,002% (111 błędów na 5 295 518
żądań, wszystkie zarejestrowane dla metody Kafka w scenariuszu obciążenia szczytowego —
podrozdział 6.3; w pozostałych scenariuszach i dla pozostałych metod odsetek błędów był
zerowy). Ze względu na przyjętą
strukturę tabel — jeden wiersz na metodę — tabele dla scenariuszy małych wiadomości oraz
dużych odpowiedzi przedstawiają wyniki dla reprezentatywnego poziomu 100 równoczesnych
użytkowników, natomiast pełną zależność opóźnienia i przepustowości od poziomu obciążenia
(10, 100, 500, 1000 użytkowników) ilustrują wykresy skalowania scenariusza obciążeniowego;
zachowanie przy 2000 użytkownikach przedstawiono osobno jako scenariusz obciążenia
szczytowego (podrozdział 6.3). Tabele dla
scenariuszy małych wiadomości i dużych odpowiedzi (@tab-wyniki-male, @tab-wyniki-duze)
przedstawiają pojedynczy punkt końcowy danej klasy (odpowiednio małe komunikaty i ładunek
50 kB), natomiast testy istotności statystycznej, wykresy skalowania oraz tabela scenariusza
szczytowego (@tab-wyniki-szczyt) operują na zagregowanym wyniku pojedynczego przebiegu —
jednostce analizy zdefiniowanej w podrozdziale 5.4, łączącej obie klasy komunikatów. Z tego
względu bezwzględne wartości przepustowości nie są wprost porównywalne między tymi dwoma
ujęciami, w przeciwieństwie do opóźnień. Wszystkie wartości
opóźnień wyrażone są w milisekundach i pochodzą z pomiaru po stronie klienta (Locust); rozmiary
serializowanych danych oraz zużycie pamięci podano w jednostkach binarnych (KiB, MiB), natomiast
docelowe rozmiary ładunku poszczególnych scenariuszy — w jednostkach dziesiętnych (kB) jako
wartości nominalne.
Zgodnie z zastrzeżeniem metodologicznym z podrozdziału 5.2 opóźnienia metod REST, gRPC
i GraphQL odpowiadają pełnemu cyklowi żądanie–odpowiedź, a metod AMQP i Kafka — czasowi
publikacji do potwierdzenia przez brokera.

== Wyniki dla małych wiadomości przy dużej częstotliwości

W scenariuszu małych wiadomości przesyłanych z wysoką częstotliwością różnice między metodami
ujawniają przede wszystkim stały narzut obsługi pojedynczego żądania oraz koszt inicjalizacji
połączenia, ponieważ rozmiar samego ładunku jest pomijalny. @tab-wyniki-male zestawia
opóźnienia oraz przepustowość dla wszystkich pięciu metod przy 100 równoczesnych
użytkownikach.

#figure(
  table(
    columns: (2fr, 1fr, 1fr, 1fr, 1.4fr),
    align: (left, center, center, center, center),
    table.header(
      [*Metoda*], [*p50 [ms]*], [*p95 [ms]*], [*p99 [ms]*], [*Przepustowość [req/s]*],
    ),
    [REST/HTTP], [20], [94], [218], [579],
    [gRPC], [< 1], [< 1], [1], [657],
    [GraphQL], [208], [384], [780], [141],
    [AMQP (RabbitMQ)], [6], [39], [91], [1039],
    [Apache Kafka], [104], [524], [780], [209],
  ),
  caption: [Wyniki dla scenariusza małych wiadomości przy dużej częstotliwości (100 użytkowników)],
)<tab-wyniki-male>

Wiersze metod AMQP i Kafka w @tab-wyniki-male opisują publikację do potwierdzenia przez
brokera, a nie pełny cykl żądanie–odpowiedź, dlatego — zgodnie z zastrzeżeniem z podrozdziału
5.2 — nie są wprost porównywalne z trzema pozostałymi wierszami; uwaga ta dotyczy zarówno
kolumn opóźnienia, jak i kolumny przepustowości. Zapis „< 1" oznacza wartość poniżej
rozdzielczości zapisu generatora obciążenia, wynoszącej jedną milisekundę, a nie zmierzone
opóźnienie zerowe.

#figure(
  image("../images/wyniki_latency_vs_users.png", width: 90%),
  caption: flex-caption(
    [Mediana opóźnienia w funkcji liczby równoczesnych użytkowników dla pięciu metod
      komunikacji],
    [Mediana opóźnienia w funkcji obciążenia],
  ),
)<rys-wyniki-male>

W scenariuszu tym gRPC osiągnął najniższe opóźnienie — mediana poniżej jednej milisekundy
oraz p99 na poziomie 1 ms — co wynika z binarnej serializacji Protocol Buffers oraz
multipleksowania strumieni HTTP/2. Metody AMQP i REST plasują się w środkowej części
zestawienia (mediana odpowiednio 6 ms i 20 ms), przy czym AMQP osiągnął najwyższą
przepustowość publikacji (1039 wiadomości na sekundę). GraphQL oraz Apache Kafka wykazały
najwyższe opóźnienia (mediana odpowiednio 208 ms i 104 ms) — w przypadku GraphQL wynika to
z narzutu parsowania i walidacji zapytania nakładającego się na pojedynczy proces roboczy
serwera, a w przypadku Kafki z narzutu batchowania i pełnego potwierdzenia zapisu
(`acks=all`). @rys-wyniki-male pokazuje, że różnice te pogłębiają się gwałtownie wraz ze
wzrostem obciążenia: mediana opóźnienia gRPC pozostaje płaska (≤ 3 ms) aż do 1000
użytkowników — a w scenariuszu obciążenia szczytowego utrzymuje się nawet przy 2000
(podrozdział 6.3) — podczas gdy pozostałe metody ulegają nasyceniu. Przy 1000 użytkownikach
mediana opóźnienia REST osiąga 1300 ms, Kafki 1166 ms, a AMQP 1060 ms; GraphQL zatrzymuje się
na 800 ms, lecz jego percentyl 99 sięga w tych warunkach 63 sekund.

Uwagi wymaga niemonotoniczny przebieg Kafki: jej mediana opóźnienia wynosi 2260 ms przy 500
użytkownikach i spada do 1166 ms przy 1000, mimo praktycznie niezmienionej przepustowości
(odpowiednio 156 i 162 żądania na sekundę). Zachowanie to jest odwrotne do oczekiwanego.
Prawdopodobnym wyjaśnieniem jest efektywniejsze grupowanie wiadomości w partie (ang.
_batching_) przy większej liczbie równolegle publikujących producentów, co częściowo
kompensuje koszt pełnego potwierdzenia zapisu, jednak rozstrzygnięcie tej kwestii wymaga
osobnego eksperymentu z kontrolowanym rozmiarem partii; obserwację odnotowano wśród ograniczeń
badania (podrozdział 7.4).

Test Kruskala–Wallisa potwierdził istotność różnic na każdym poziomie obciążenia
(p < 0,001). Testy post-hoc Dunna z korektą Bonferroniego przeprowadzono osobno dla każdego
poziomu obciążenia, aby nie zestawiać w jednej próbie przebiegów różniących się opóźnieniem o
trzy rzędy wielkości; ich wyniki zestawia @tab-dunn.

#figure(
  table(
    columns: (1fr, 3.2fr),
    align: (center + horizon, left + horizon),
    table.header(
      [*Liczba użytkowników*], [*Pary metod różniące się istotnie (p < 0,05)*],
    ),
    [10], [gRPC–Kafka (< 0,001), gRPC–GraphQL (0,007), AMQP–Kafka (0,050), Kafka–REST (0,050)],
    [100], [gRPC–GraphQL (< 0,001), gRPC–Kafka (0,012), AMQP–GraphQL (0,012)],
    [500], [gRPC–Kafka (< 0,001), gRPC–REST (0,012), AMQP–Kafka (0,012)],
    [1000], [gRPC–REST (< 0,001), GraphQL–REST (0,026), gRPC–AMQP (0,028)],
  ),
  caption: [Pary metod różniące się istotnie w teście post-hoc Dunna, per poziom obciążenia],
)<tab-dunn>

Liczba par osiągających próg istotności jest niewielka, co wynika z ograniczonej mocy testu
przy trzech do pięciu powtórzeń na poziom, a nie z braku różnic — o ich skali świadczą różnice
względne sięgające kilkuset procent oraz powtarzalność wzorca między niezależnymi przebiegami.
Istotny jest przy tym kierunek zmian widoczny w @tab-dunn: przewaga gRPC nad REST nie osiąga
progu istotności przy 10 i 100 użytkownikach (odpowiednio p = 0,92 i p = 0,30), a staje się
istotna dopiero przy 500 i 1000 (p = 0,012 i p < 0,001). Przewaga ta ujawnia się zatem jako
zjawisko obciążeniowe, a nie stały narzut różnicujący protokoły niezależnie od warunków
pracy — co jest zgodne z płaskim przebiegiem krzywej gRPC na @rys-wyniki-male.

Do analizy statystycznej wchodzi pięć powtórzeń na poziom obciążenia, z wyjątkiem sześciu
spośród dwudziestu kombinacji metody i poziomu, w których filtr rozstępu międzykwartylowego
odrzucił od jednego do dwóch przebiegów; najmniej liczna jest kombinacja REST przy 1000
użytkownikach (n = 3). Pełne liczebności zawiera plik `statistical_analysis_by_level.csv`.

Obok istotności statystycznej oceniono również skalę różnic za pomocą rozmiaru efektu testu
Kruskala–Wallisa (współczynnik epsilon-kwadrat). Dla całego scenariusza obciążeniowego
współczynnik ε² wyniósł około 0,50, co oznacza, że blisko połowa zmienności rang opóźnienia
jest wyjaśniona samym wyborem metody komunikacji — wartość ta wielokrotnie przekracza umowny
próg dużego efektu (0,14). Na poszczególnych poziomach obciążenia rozdział między metodami jest
przy tym niemal pełny, przez co estymatory rozmiaru efektu osiągają wartości graniczne; jako
miarę zachowawczą podano oszacowanie zbiorcze.

Uzupełnieniem porównania jest wariant _echo_, w którym serwer odsyła 256 bajtów bez
przetwarzania, co pozwala oszacować sam narzut protokołu. Przy 100 użytkownikach mediana
opóźnienia wyniosła w nim 20 ms dla REST, poniżej 1 ms dla gRPC oraz 206 ms dla GraphQL —
wartości niemal identyczne jak dla małych komunikatów (odpowiednio 20 ms, poniżej 1 ms
i 208 ms). Oznacza to, że w badanym zakresie o opóźnieniu decyduje niemal wyłącznie stały
koszt obsługi pojedynczego żądania, a nie koszt przetworzenia ładunku. Dla metod
asynchronicznych wariant ten nie ma odpowiednika, ponieważ publikacja do kolejki nie zwraca
odpowiedzi.

Komplementarny obraz daje analiza przepustowości w funkcji obciążenia (@rys-throughput).
Przepustowość wszystkich metod rośnie do poziomu około stu użytkowników, po czym maleje, co
wynika z dwóch nakładających się zjawisk. Dla metod wolniejszych (GraphQL, Kafka) spadek
odzwierciedla nasycenie serwera — rosnące opóźnienie ogranicza liczbę żądań obsłużonych w
jednostce czasu. Dla metod najszybszych (gRPC, AMQP, REST) górnym ograniczeniem staje się
natomiast wydajność jednoprocesowego generatora obciążenia, a nie serwera; dlatego to
opóźnienie, a nie surowa przepustowość, najwierniej charakteryzuje zachowanie tych metod pod
wysokim obciążeniem (podrozdział 7.4). Najwyższą przepustowość w szczycie osiągnął AMQP
(ponad 1180 wiadomości na sekundę przy stu użytkownikach), a wśród metod synchronicznych —
gRPC (ponad 1020 żądań na sekundę).

#figure(
  image("../images/wyniki_throughput_vs_users.png", width: 90%),
  caption: flex-caption(
    [Przepustowość w funkcji liczby równoczesnych użytkowników dla pięciu metod komunikacji],
    [Przepustowość w funkcji obciążenia],
  ),
)<rys-throughput>

== Wyniki dla dużych odpowiedzi

W scenariuszu przesyłania dużych odpowiedzi dominującym czynnikiem wydajnościowym staje się
koszt serializacji, deserializacji oraz transmisji danych. W tym scenariuszu szczególnego
znaczenia nabiera różnica między tekstowym formatem JSON a binarnymi formatami serializacji.
@tab-wyniki-duze przedstawia wyniki dla ładunku o docelowym rozmiarze 50 kB przy 100
użytkownikach.

#figure(
  table(
    columns: (2fr, 1fr, 1fr, 1fr, 1.4fr),
    align: (left, center, center, center, center),
    table.header(
      [*Metoda*], [*p50 [ms]*], [*p95 [ms]*], [*p99 [ms]*], [*Przepustowość [MiB/s]*],
    ),
    [REST/HTTP], [24], [138], [446], [3,00],
    [gRPC], [3], [4], [9], [2,43],
    [GraphQL], [188], [434], [742], [0,83],
    [AMQP (RabbitMQ)], [10], [67], [278], [3,05],
    [Apache Kafka], [340], [642], [820], [1,47],
  ),
  caption: [Wyniki dla scenariusza dużych odpowiedzi (ładunek 50 kB, 100 użytkowników)],
)<tab-wyniki-duze>

#figure(
  image("../images/wyniki_latency_vs_payload.png", width: 90%),
  caption: flex-caption(
    [Mediana opóźnienia w zależności od rozmiaru ładunku (50 i 100 kB) dla poszczególnych
      metod],
    [Opóźnienie w funkcji rozmiaru ładunku],
  ),
)<rys-wyniki-duze>

Również w tym scenariuszu gRPC uzyskał najniższe opóźnienie (mediana 3 ms, p99 9 ms), a jego
binarna reprezentacja okazała się znacznie bardziej zwarta niż równoważny format tekstowy JSON
metody REST — średni rozmiar odpowiedzi wyniósł 32,9 KiB wobec 40,6 KiB, co potwierdza
teoretyczną przewagę Protocol Buffers pod względem gęstości serializacji.

Zestawienie to wymaga jednak dopełnienia. Odpowiedź GraphQL w wariancie pobierającym komplet
pól ma rozmiar 32,5 KiB, a więc praktycznie identyczny z binarnym protobufem, natomiast w
wariancie z selekcją podzbioru pól spada do 6,7 KiB — blisko pięciokrotnie poniżej gRPC.
O rozmiarze przesyłanych danych decyduje zatem w pierwszej kolejności zakres pobieranych pól,
a dopiero w drugiej format serializacji. Jest to zarazem jedyny mierzalny w niniejszym badaniu
przejaw deklarowanej przewagi GraphQL w zakresie eliminacji nadmiarowych danych (ang.
_over-fetching_).

Wartości przepustowości wyrażonej w
mebibajtach na sekundę wymagają ostrożnej interpretacji: przy 100 użytkownikach i odstępie
0,1–0,5 s między żądaniami klasy generującej duże żądania przepustowość metod niesaturujących
(gRPC, REST, AMQP) jest ograniczona tempem generowania ruchu po stronie klienta, a nie
możliwościami serwera — stąd zbliżone wartości rzędu 2,4–3,1 MiB/s. Miarodajna różnica
dotyczy metod wolniejszych: GraphQL (0,83 MiB/s) i Kafka (1,47 MiB/s) nie nadążają z obsługą
ruchu, co przekłada się na wyraźnie niższą efektywną przepustowość i wysokie opóźnienia
(mediana odpowiednio 188 ms i 340 ms).

== Wyniki obciążenia szczytowego

Scenariusz obciążenia szczytowego ujawnia różnice w mechanizmach kontroli przeciążenia oraz
degradacji usługi. Metody synchroniczne i asynchroniczne reagują na nagły wzrost obciążenia w
odmienny sposób — w metodach synchronicznych przeciążenie prowadzi do gwałtownego wzrostu
opóźnień, natomiast metody asynchroniczne buforują nadmiarowy ruch w kolejce lub logu.
@tab-wyniki-szczyt zestawia wyniki dla nagłego skoku do 2000 równoczesnych użytkowników.

#figure(
  table(
    columns: (2fr, 1.4fr, 1.2fr, 1.2fr),
    align: (left, center, center, center),
    table.header(
      [*Metoda*], [*Przepustowość [req/s]*], [*p99 [ms]*], [*Odsetek błędów [%]*],
    ),
    [REST/HTTP], [289], [58 333], [0,000],
    [gRPC], [420], [9], [0,000],
    [GraphQL], [181], [60 000], [0,000],
    [AMQP (RabbitMQ)], [420], [3 767], [0,000],
    [Apache Kafka], [159], [5 800], [0,375],
  ),
  caption: [Wyniki dla scenariusza obciążenia szczytowego (2000 użytkowników)],
)<tab-wyniki-szczyt>

#figure(
  image("../images/wyniki_spike.png", width: 90%),
  caption: flex-caption(
    [Przebieg mediany opóźnienia oraz odsetka błędów w czasie podczas obciążenia szczytowego],
    [Opóźnienie i błędy podczas obciążenia szczytowego],
  ),
)<rys-wyniki-szczyt>

Pod nagłym obciążeniem 2000 użytkowników gRPC zachował p99 na poziomie 9 ms — praktycznie
niezmienionym względem niższych poziomów obciążenia — co świadczy o braku nasycenia serwera.
Metody REST i GraphQL wykazały skrajną degradację: p99 osiągnęło odpowiednio 58 i 60 sekund,
przy czym warto zaznaczyć, że wysokie opóźnienie nie przełożyło się na błędy (odsetek błędów
0%), ponieważ żądania były kolejkowane i ostatecznie obsługiwane, a nie odrzucane. Jedyną
metodą, która zarejestrowała rzeczywiste błędy, była Kafka (0,375%), co wynikało z nielicznych
przekroczeń limitu czasu wysyłki w chwili, gdy broker został chwilowo przeciążony jednoczesnym
startem dwóch tysięcy producentów (zjawisko opisane w rozdziale dotyczącym trudności
implementacyjnych). Wartości
przepustowości w tym scenariuszu należy odczytywać łącznie z opóźnieniem — dla metod
najszybszych (gRPC) górnym ograniczeniem może być wydajność samego generatora obciążenia
działającego w pojedynczym procesie, dlatego to opóźnienie i odsetek błędów, a nie surowa
przepustowość, najlepiej charakteryzują zachowanie usługi pod przeciążeniem.

Przebieg czasowy przedstawiony na @rys-wyniki-szczyt ujawnia mechanizm reakcji na przeciążenie.
W metodach synchronicznych oraz w kolejkowym AMQP opóźnienie narasta stromo w ciągu pierwszych
kilkunastu sekund — w miarę jak liczba równoczesnych użytkowników osiąga docelowe dwa tysiące —
po czym ustala się na wysokim poziomie i nie powraca do wartości wyjściowych przed końcem testu
(REST stabilizuje się około 1300 ms, GraphQL około 690 ms, AMQP około 1600 ms, a Kafka około
1900–2100 ms). Jest to sygnatura narastania kolejki pod trwałym przeciążeniem, a nie
przejściowego piku, po którym następuje odbudowa. gRPC stanowi wyjątek: jego mediana opóźnienia
pozostaje płaska (poniżej trzech milisekund) przez cały przebieg, co oznacza, że serwer nie
wchodzi w reżim przeciążenia nawet przy nagłym skoku obciążenia.

== Wyniki długotrwałych połączeń

Scenariusz długotrwałych połączeń bada stabilność metod w wydłużonym horyzoncie czasowym.
Analiza koncentruje się na tym, czy wydajność utrzymuje się na stałym poziomie, czy też
następuje jej stopniowa degradacja, mogąca świadczyć o wyciekach zasobów lub problemach z
zarządzaniem połączeniami. @tab-wyniki-dlugotrwale porównuje medianę opóźnienia z początkowej
i końcowej fazy pięciominutowego przebiegu (uśrednioną z trzech powtórzeń).

#figure(
  table(
    columns: (2fr, 1.4fr, 1.4fr, 1fr),
    align: (left, center, center, center),
    table.header(
      [*Metoda*], [*p50 [ms] (początek)*], [*p50 [ms] (koniec)*], [*Stabilność*],
    ),
    [REST/HTTP], [4], [4], [stabilna],
    [gRPC], [< 1], [< 1], [stabilna],
    [GraphQL], [40], [42], [stabilna],
    [AMQP (RabbitMQ)], [2], [2], [stabilna],
    [Apache Kafka], [45], [46], [stabilna],
  ),
  caption: [Wyniki dla scenariusza długotrwałych połączeń],
)<tab-wyniki-dlugotrwale>

#figure(
  image("../images/wyniki_longrun.png", width: 90%),
  caption: flex-caption(
    [Przebieg mediany opóźnienia oraz odsetka błędów w czasie testu długotrwałego],
    [Opóźnienie w czasie — test długotrwały],
  ),
)<rys-wyniki-dlugotrwale>

Wszystkie pięć metod zachowało stabilną wydajność przez cały czas trwania testu — wzrost
mediany opóźnienia między fazą początkową a końcową nie przekroczył 4,2% dla żadnej z metod
(wartość najwyższa dotyczy GraphQL, gdzie mediana wzrosła z 40,3 do 42,0 ms),
a odsetek błędów przez całe pięć minut pozostał zerowy (dolny panel @rys-wyniki-dlugotrwale).
Nie zaobserwowano dryfu opóźnienia w górę, który świadczyłby o wyciekach pamięci lub
narastającej degradacji. Widoczne na wykresie początkowe, wyższe wartości dla Kafki i AMQP
odpowiadają fazie rozgrzewania połączeń i ustępują w ciągu pierwszych kilku sekund,
po czym opóźnienie ustala się na stałym poziomie.

Przebieg czasowy na @rys-wyniki-dlugotrwale uwidacznia tę stabilność bezpośrednio: po ustaleniu
się w pierwszych sekundach okna pomiarowego krzywe mediany opóźnienia wszystkich metod
przebiegają niemal poziomo przez pozostałe niemal pięć minut, bez trendu wzrostowego ani
okresowych skoków. Dla gRPC i AMQP krzywe pokrywają się praktycznie z poziomem bliskim zeru
(poniżej 1 ms oraz około 2 ms), natomiast dla GraphQL i Kafki utrzymują się na nieco wyższym,
lecz równie płaskim poziomie (odpowiednio około 42 ms i 46 ms). Zbieżność wartości z początku
i końca okna, ujęta liczbowo w @tab-wyniki-dlugotrwale, potwierdza brak kumulatywnych efektów
degradacji w testowanych implementacjach.

== Analiza zużycia zasobów systemowych

Ostatnia część rozdziału przedstawia porównanie zużycia zasobów systemowych — obciążenia
procesora oraz wykorzystania pamięci operacyjnej — mierzonego narzędziem cAdvisor dla
komponentu serwerowego każdej metody. Metryki te są istotne z punktu widzenia kosztów
eksploatacji systemu. Wartości obciążenia procesora wyrażono w procentach jednego rdzenia
(limit kontenera wynosił dwa rdzenie, tj. 200%); dla metod asynchronicznych podano zużycie
brokera, stanowiące dominujący składnik kosztu.

Zasadnicze znaczenie dla porównywalności tych wartości ma okno uśredniania. Narzędzie cAdvisor
próbkuje wszystkie kontenery przez cały czas trwania kampanii, w którym każdy protokół jest
obciążany tylko przez około jedną piątą czasu; uśrednienie brokera po całym oknie kampanii
mieszałoby jego pracę pod obciążeniem z okresami bezczynności podczas testów pozostałych
protokołów i nie byłoby porównywalne z serwerem uśrednionym w ten sam sposób. Dlatego wszystkie
wartości w @tab-wyniki-zasoby wyznaczono w oknie aktywności tego protokołu, którego dany
komponent dotyczy (56–74 minuty na protokół); obliczenia zawiera plik
`resource_usage_by_window.csv`.

#figure(
  table(
    columns: (2fr, 1.2fr, 1.2fr, 1fr),
    align: (left, center, center, center),
    table.header(
      [*Metoda (komponent)*], [*Śr. CPU [%]*], [*Maks. CPU [%]*], [*Maks. RAM [MiB]*],
    ),
    [REST/HTTP (serwer)], [68], [100], [79],
    [gRPC (serwer)], [63], [88], [42],
    [GraphQL (serwer)], [80], [100], [63],
    [AMQP (broker RabbitMQ)], [29], [42], [850],
    [Apache Kafka (broker)], [18], [23], [1024],
  ),
  caption: [Zużycie zasobów systemowych komponentu serwerowego w oknie aktywności protokołu],
)<tab-wyniki-zasoby>

#figure(
  image("../images/wyniki_resources.png", width: 95%),
  caption: flex-caption(
    [Szczytowe zużycie procesora i pamięci operacyjnej przez kontenery w oknie kampanii],
    [Szczytowe zużycie CPU i RAM przez kontenery],
  ),
)<rys-wyniki-zasoby>

Zestawienie ujawnia dwie odmienne charakterystyki zużycia zasobów. Serwery metod
synchronicznych (REST, gRPC, GraphQL) są ograniczone przez procesor — ich obciążenie zbliża
się do 100% jednego rdzenia (co odzwierciedla działanie w pojedynczym procesie roboczym
ograniczonym przez globalną blokadę interpretera Pythona), przy niewielkim zużyciu pamięci
(42–79 MiB). Metody asynchroniczne wykazują odwrotny profil: brokery RabbitMQ i Kafka zużywają
istotnie mniej procesora (średnio 29% i 18%, a więc od dwóch do czterech razy mniej niż serwery
synchroniczne), lecz znacząco więcej pamięci (850 MiB i 1024 MiB), przy
czym broker Kafki osiągnął zadeklarowany limit pamięci kontenera, co odpowiada buforowaniu
segmentów trwałego logu w pamięci podręcznej. Zużycie zasobów przez procesy konsumentów jest
w obu metodach asynchronicznych wyraźnie niższe niż przez brokery i wynosi średnio 11,9%
procesora oraz 29 MiB pamięci dla AMQP i 6,6% procesora oraz 43 MiB pamięci dla Kafki. Wysoka
efektywność procesorowa gRPC (najniższe
szczytowe obciążenie wśród serwerów synchronicznych — 88% — oraz najniższe zużycie pamięci —
42 MiB) dodatkowo potwierdza jego przewagę wydajnościową obserwowaną w pozostałych
scenariuszach.

== Latencja end-to-end metod asynchronicznych

Opóźnienia metod asynchronicznych raportowane w dotychczasowych podrozdziałach odpowiadają
publikacji do potwierdzenia przez brokera (publish→ACK) i nie obejmują czasu oczekiwania
wiadomości w kolejce lub logu ani jej odbioru przez konsumenta. Pełną ścieżkę dostarczenia —
od publikacji do skonsumowania wiadomości — rejestruje osobna metryka latencji koniec–koniec
(ang. _end-to-end_), zdefiniowana w podrozdziale 5.2 i zbierana po stronie konsumenta jako
histogram w systemie Prometheus. @tab-e2e przedstawia jej percentyle wyznaczone metodą
`histogram_quantile` dla całej kampanii pomiarowej.

#figure(
  table(
    columns: (2fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center),
    table.header([*Metoda*], [*p50 [ms]*], [*p95 [ms]*], [*p99 [ms]*]),
    [AMQP (RabbitMQ)], [4], [24], [69],
    [Apache Kafka], [90], [463], [898],
  ),
  caption: [Latencja koniec–koniec (publikacja → odebranie przez konsumenta) metod
    asynchronicznych],
)<tab-e2e>

Wartości w @tab-e2e agregują wszystkie poziomy obciążenia, nie są więc wprost porównywalne
liczbowo z percentylami publikacji z tabel dla poszczególnych poziomów; służą charakterystyce
całego potoku dostarczania. Dla AMQP latencja koniec–koniec pozostaje bardzo niska (mediana
4 ms), jedynie nieznacznie przewyższając samą publikację — konsument nadąża z odbiorem, a
kolejka nie narasta. Dla Kafki jest ona ponad dwudziestokrotnie wyższa (mediana 90 ms, p99
poniżej jednej sekundy), co odzwierciedla narzut batchowania, dopisywania do trwałego logu
oraz pobierania wiadomości przez konsumenta na całej ścieżce dostarczania. Istotne jest, że w
obu przypadkach latencja koniec–koniec pozostała ograniczona (p99 poniżej jednej sekundy)
przez cały czas trwania eksperymentu, co potwierdza, że konsumenci nadążali z przetwarzaniem,
a raportowane opóźnienia publikacji nie maskują narastającego zaległego ruchu (ang.
_backlog_).

== Przepustowość metod asynchronicznych w trybie natywnym

Przepustowość metod AMQP i Kafka przedstawiona w poprzednich podrozdziałach odpowiada
publikacji synchronicznej — z oczekiwaniem na potwierdzenie każdej pojedynczej wiadomości —
którą przyjęto dla porównywalności latencji z metodami synchronicznymi (podrozdział 5.2).
Tryb ten świadomie pomija asynchroniczne batchowanie i potokowość, będące podstawowym
mechanizmem, dzięki któremu pośrednicy wiadomości osiągają wysoką przepustowość. Aby ocenić
rzeczywisty pułap przepustowości tych metod, przeprowadzono dodatkowy pomiar, w którym
producent publikował wiadomości w trybie natywnym — z maksymalną prędkością, bez blokującego
oczekiwania na potwierdzenie każdej wiadomości. Jako miarę przyjęto przepustowość dostarczoną,
odczytaną po stronie konsumenta (liczba wiadomości faktycznie odebranych i przetworzonych na
sekundę), co odzwierciedla rzeczywisty potok end-to-end, a nie samo zapełnianie bufora.

#figure(
  table(
    columns: (2fr, 1.6fr, 1.6fr, 1fr),
    align: (left, center, center, center),
    table.header(
      [*Metoda*],
      [*Publikacja synchroniczna [msg/s]*],
      [*Tryb natywny async [msg/s]*],
      [*Krotność*],
    ),
    [AMQP (RabbitMQ)], [1 039], [≈ 4 200], [≈ 4×],
    [Apache Kafka], [209], [≈ 5 000], [≈ 24×],
  ),
  caption: [Przepustowość metod asynchronicznych: publikacja synchroniczna
    (przy 100 użytkownikach) wobec trybu natywnego z batchowaniem],
)<tab-async-throughput>

Wyniki zebrane w @tab-async-throughput potwierdzają, że niska przepustowość Kafki
zaobserwowana w podstawowym porównaniu jest artefaktem synchronicznego trybu pomiaru, a nie
inherentną cechą tej platformy. W trybie natywnym Kafka osiągnęła przepustowość dostarczoną
około dwudziestoczterokrotnie wyższą, podczas gdy AMQP — jedynie czterokrotnie. Różnica ta
jest spójna z architekturą obu systemów: przepustowość Kafki opiera się na batchowaniu, które
synchroniczne potwierdzanie każdej wiadomości w praktyce neutralizuje, natomiast przepustowość
RabbitMQ wynika przede wszystkim ze współbieżności wielu kanałów, częściowo obecnej już w
teście wieloużytkownikowym. W obu przypadkach osiągnięty pułap (rzędu pięciu–sześciu tysięcy
wiadomości na sekundę) był ograniczony wydajnością jednowątkowego konsumenta w języku Python,
a nie możliwościami samych brokerów — co wpisuje się w ograniczenia ekosystemu Pythona
omówione w podrozdziale 7.3. Wartości w @tab-async-throughput należy traktować jako szacunek
rzędu wielkości, a nie precyzyjny pomiar wielokrotny: pochodzą z niewielkiej liczby przebiegów,
których okna odczytu przepustowości dostarczonej częściowo się pokrywały, dlatego podano je
w postaci przybliżonej (krotności „≈ 4×" i „≈ 24×" oddają rząd różnicy, nie dokładny mnożnik).
Obie kolumny @tab-async-throughput pochodzą ponadto z różnych punktów pomiaru: publikacja
synchroniczna mierzona jest po stronie klienta (generator obciążenia), natomiast tryb natywny —
po stronie konsumenta. Krotność należy zatem odczytywać jako porównanie pułapu całego potoku
z tempem publikacji pojedynczych wiadomości, a nie jako przyspieszenie tej samej operacji.

== Trwałość i odporność na awarię konsumenta

Wszystkie dotychczasowe pomiary dotyczyły wydajności. Metody asynchroniczne posiadają jednak
właściwość, której model żądanie–odpowiedź nie zapewnia z zasady: odporność na awarię odbiorcy
bez utraty danych. Aby ją zweryfikować eksperymentalnie, przeprowadzono dodatkowy test.
Opublikowano 20 000 wiadomości opatrzonych unikalnymi, kolejnymi identyfikatorami; pierwszy
konsument przetwarzał je do około połowy, po czym jego połączenie było gwałtownie zamykane
(symulacja awarii), a następnie uruchamiano drugiego konsumenta, który dokańczał odbiór.
Zbadano, czy każdy opublikowany identyfikator został ostatecznie odebrany.

#figure(
  table(
    columns: (2fr, 1.3fr, 1.4fr, 1fr, 1.1fr),
    align: (left, center, center, center, center),
    table.header(
      [*Metoda*], [*Opublikowane*], [*Odebrane (unikalne)*], [*Utracone*], [*Duplikaty*],
    ),
    [AMQP (RabbitMQ)], [20 000], [20 000], [0], [1],
    [Apache Kafka], [20 000], [20 000], [0], [0],
  ),
  caption: [Trwałość dostarczania przy symulowanej awarii konsumenta],
)<tab-trwalosc>

Jak przedstawiono w @tab-trwalosc, obie metody dostarczyły komplet wiadomości mimo awarii
konsumenta — utrata wyniosła zero. Mechanizmy zapewniające tę gwarancję są jednak odmienne:
Kafka wznowiła odbiór od ostatnio zatwierdzonego przesunięcia (ang. _offset_) w trwałym logu,
w którym wiadomości pozostają zapisane niezależnie od stanu konsumenta, natomiast RabbitMQ
zwrócił do kolejki wiadomości pobrane, lecz niepotwierdzone przez konsumenta w chwili awarii,
i dostarczył je ponownie. Pojedynczy duplikat zaobserwowany dla AMQP jest bezpośrednią
ilustracją gwarancji dostarczenia co najmniej raz (ang. _at-least-once_): wiadomość będąca w
locie w momencie awarii została dostarczona powtórnie. Wynik ten stanowi empiryczne
potwierdzenie cech przypisanych metodom asynchronicznym w macierzy decyzyjnej — trwałości logu
Kafki oraz gwarancji dostarczenia i rozprzęgnięcia AMQP — i unaocznia zasadniczą różnicę wobec
metod synchronicznych, w których awaria serwera w trakcie obsługi żądania oznacza jego utratę
i błąd po stronie klienta.
