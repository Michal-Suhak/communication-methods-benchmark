#import "../utils.typ": todo, silentheading, flex-caption

= Metodologia pomiarów <metodologia>

Rozdział piąty opisuje metodologię przeprowadzonych badań empirycznych. Omówiono w nim
procedurę przeprowadzania testów obciążeniowych, dobór scenariuszy testowych, zestaw
mierzonych metryk oraz metody analizy statystycznej uzyskanych wyników. Precyzyjne
zdefiniowanie metodologii ma kluczowe znaczenie dla powtarzalności badania oraz dla
wiarygodności formułowanych na jego podstawie wniosków.

== Scenariusze testowe

Aby porównanie odzwierciedlało rzeczywiste warunki eksploatacji systemów rozproszonych,
zdefiniowano cztery scenariusze testowe odpowiadające typowym wzorcom obciążenia spotykanym w
praktyce inżynierskiej. Każdy scenariusz uwypukla inny aspekt charakterystyki wydajnościowej
badanych metod.

+ *Małe wiadomości przy dużej częstotliwości* — scenariusz symulujący intensywną wymianę
  niewielkich komunikatów, w którym dominującym czynnikiem jest narzut inicjalizacyjny oraz
  stały koszt obsługi pojedynczego żądania, niezależny od rozmiaru ładunku.
+ *Przesyłanie dużych odpowiedzi* — scenariusz, w którym rozmiar pojedynczego ładunku jest
  znaczący, przez co dominującym czynnikiem staje się koszt serializacji, deserializacji oraz
  transmisji danych.
+ *Obciążenie szczytowe* — scenariusz polegający na gwałtownym wzroście liczby równoczesnych
  żądań, mający na celu zbadanie zachowania każdej metody w warunkach przeciążenia, w tym
  mechanizmów kontroli przeciążenia (ang. _backpressure_) oraz degradacji jakości usługi.
+ *Długotrwałe połączenia* — scenariusz badający stabilność i wydajność metod w dłuższym
  horyzoncie czasowym, ujawniający ewentualne wycieki zasobów lub stopniową degradację
  wydajności.

Dla każdego scenariusza zdefiniowano parametry takie jak rozmiar ładunku, liczba
równoczesnych klientów oraz docelowa częstotliwość żądań. Parametry te są jednakowe dla
wszystkich badanych metod w obrębie danego scenariusza, co zapewnia rzetelność porównania.
Scenariusze małych wiadomości i dużych odpowiedzi realizowane są w jednym przebiegu
pomiarowym: populacja wirtualnych użytkowników dzielona jest po połowie na klasę
generującą małe komunikaty (odstęp 0,01–0,05 s między żądaniami) oraz klasę pobierającą
duże odpowiedzi (odstęp 0,1–0,5 s) — struktura ta jest identyczna we wszystkich pięciu
protokołach. Dodatkowo dla protokołów żądanie–odpowiedź (REST, gRPC, GraphQL) mierzony
jest wariant _echo_ — odesłanie 256 bajtów bez przetwarzania — służący ocenie czystego
narzutu protokołu; dla metod asynchronicznych wariant ten pominięto, ponieważ publikacja
do kolejki nie ma odpowiednika odpowiedzi zwrotnej.

#figure(
  table(
    columns: (2fr, 1fr, 1fr, 1fr),
    align: left + horizon,
    table.header(
      [*Scenariusz*], [*Rozmiar ładunku*], [*Liczba klientów*], [*Czas trwania*],
    ),
    [Małe wiadomości, duża częstotliwość], [\~0,1–0,5 kB], [10–1000 (połowa populacji)], [60 s na poziom],
    [Duże odpowiedzi], [50 i 100 kB], [10–1000 (połowa populacji)], [60 s na poziom],
    [Obciążenie szczytowe], [miks małych i dużych], [2000 (przyrost 200/s)], [60 s],
    [Długotrwałe połączenia], [miks małych i dużych], [50 (stały poziom)], [300 s],
  ),
  caption: [Parametry scenariuszy testowych],
)<tab-scenariusze>

Poziomy obciążenia w scenariuszach małych wiadomości i dużych odpowiedzi wynoszą 10, 100,
500 oraz 1000 równoczesnych użytkowników. Poziom 50 użytkowników przypisany jest wyłącznie
scenariuszowi długotrwałemu, a 2000 — scenariuszowi obciążenia szczytowego; nie są one
punktami krzywej skalowania scenariusza obciążeniowego.

== Mierzone metryki

W ramach badania mierzono trzy zasadnicze grupy metryk wydajnościowych. Pierwszą grupę
stanowi opóźnienie, mierzone nie jako wartość średnia, lecz w postaci percentyli p50, p95 i
p99. Zastosowanie percentyli zamiast średniej arytmetycznej jest celowe — średnia maskuje
wartości skrajne, podczas gdy w systemach produkcyjnych to właśnie ogon rozkładu opóźnień,
reprezentowany przez wysokie percentyle, decyduje o postrzeganej jakości usługi.

Istotnym zastrzeżeniem metodologicznym jest odmienna semantyka opóźnienia dla dwóch rodzin
protokołów. Dla metod synchronicznych (REST, gRPC, GraphQL) mierzone jest pełne opóźnienie
w obie strony (ang. _round-trip_) po stronie klienta: od wysłania żądania do otrzymania
kompletnej odpowiedzi. Dla metod asynchronicznych mierzone jest opóźnienie publikacji: czas
od wysłania wiadomości do potwierdzenia jej przyjęcia przez brokera — w AMQP z użyciem
mechanizmu potwierdzeń publikacji (ang. _publisher confirms_), w Kafce z pełnym
potwierdzeniem zapisu (`acks=all`). Obie wielkości asynchroniczne są wzajemnie porównywalne,
lecz nie są wprost porównywalne z opóźnieniem round-trip — wiadomość potwierdzona przez
brokera nie została jeszcze przetworzona przez odbiorcę. Z tego względu dla metod
asynchronicznych rejestrowana jest dodatkowo, jako osobna metryka, latencja typu koniec–koniec
(ang. _end-to-end_): czas od publikacji wiadomości do jej odebrania przez konsumenta,
obejmujący czas oczekiwania w kolejce lub logu. Wnioski porównawcze w rozdziale szóstym
formułowane są z uwzględnieniem tego rozróżnienia.

Drugą grupę metryk stanowi przepustowość, wyrażona liczbą pomyślnie obsłużonych żądań na
sekundę dla metod synchronicznych lub liczbą przetworzonych wiadomości na sekundę dla metod
asynchronicznych. Trzecią grupę tworzą metryki zużycia zasobów systemowych, obejmujące
procentowe obciążenie procesora oraz wykorzystanie pamięci operacyjnej przez komponenty
serwerowe i pośredniczące. Dodatkowo rejestrowano rozmiar serializowanego ładunku danych,
stanowiący istotny czynnik różnicujący formaty tekstowe i binarne.

== Procedura pomiarowa

Procedura pomiarowa została zaprojektowana w sposób minimalizujący wpływ czynników
zakłócających. Każdy pomiar poprzedzony był fazą rozgrzewki, podczas której system osiągał
stan ustalony, a wyniki z tej fazy nie były uwzględniane w analizie. Faza rozgrzewki ma
szczególne znaczenie dla środowisk opartych na maszynach wirtualnych oraz mechanizmach
buforowania, w których początkowa wydajność może odbiegać od wydajności w stanie ustalonym.
Należy przy tym zaznaczyć, że rozgrzewka wykonywana jest w osobnym procesie generatora
obciążenia — doprowadza do stanu ustalonego serwery i pośredników, natomiast pule połączeń
klienta budowane są od nowa na początku właściwego okna pomiarowego; koszt ten, jednakowy
dla wszystkich metod, zawiera się w pierwszych sekundach każdego pomiaru.

Dla każdego scenariusza oraz każdej metody komunikacji przeprowadzono wiele niezależnych
powtórzeń pomiaru, co umożliwiło oszacowanie zmienności wyników oraz odrzucenie pomiarów
obarczonych przypadkowymi zakłóceniami. Pomiędzy kolejnymi pomiarami środowisko było
przywracane do stanu początkowego, aby wyeliminować wpływ pozostałości po poprzednich
testach. Wszystkie metryki zbierane były automatycznie przez eksporter Prometheus i
wizualizowane w dashboardach Grafana, co zapewniło jednolity i obiektywny sposób akwizycji
danych.

#figure(
  table(
    columns: (1fr, 1fr),
    align: left + horizon,
    table.header([*Parametr*], [*Wartość*]),
    [Liczba powtórzeń na scenariusz], [5 (obciążeniowy), 3 (szczytowy), 3 (długotrwały)],
    [Czas trwania pojedynczego testu], [60 s (300 s dla długotrwałego)],
    [Czas trwania fazy rozgrzewki], [30 s (wyniki odrzucane)],
    [Przerwa stabilizacyjna między pomiarami], [15 s],
    [Częstotliwość próbkowania metryk], [5 s (Prometheus)],
  ),
  caption: [Parametry procedury pomiarowej],
)<tab-procedura>

Podana w @tab-procedura liczba powtórzeń odnosi się do przebiegów wykonanych. Do analizy
statystycznej wchodzą przebiegi pozostałe po odrzuceniu wartości odstających metodą rozstępu
międzykwartylowego, przez co liczebność części grup jest mniejsza; szczegółowe liczebności
podano w podrozdziale 6.1.

== Analiza statystyczna

Zebrane dane poddano analizie statystycznej w celu zapewnienia wiarygodności i
obiektywności porównania. Dla każdej kombinacji metody i scenariusza wyznaczono miary
tendencji centralnej oraz miary rozproszenia, w tym medianę, percentyle oraz odchylenie
standardowe, co pozwoliło ocenić zarówno typową wydajność, jak i jej stabilność.

W celu stwierdzenia, czy zaobserwowane różnice między metodami są istotne statystycznie, a
nie wynikają z losowej zmienności pomiarów, zastosowano dwustopniową procedurę testowania.
Normalność rozkładu w każdej grupie weryfikowana jest testem Shapiro–Wilka, przy czym test
ten wykonywany jest wyłącznie dla grup o liczebności co najmniej 20 obserwacji — przy
mniejszej liczbie powtórzeń nie ma on wystarczającej mocy, dlatego przyjmowana jest wówczas
bezpośrednio ścieżka nieparametryczna. Jeżeli wszystkie grupy mają rozkład zbliżony do
normalnego, stosowana jest jednoczynnikowa analiza wariancji (ANOVA) z testem post-hoc
Tukeya; w przeciwnym razie — nieparametryczny test Kruskala–Wallisa z testem post-hoc Dunna
i korektą Bonferroniego dla porównań wielokrotnych. Dodatkowo, dla oceny nie tylko istotności,
lecz także skali różnic, wyznaczany jest rozmiar efektu testu Kruskala–Wallisa w postaci
współczynnika epsilon-kwadrat (ε²), wyrażającego udział zmienności rang wyjaśniony przez
przynależność do metody.
Test zbiorczy (ang. _omnibus_) rozstrzyga jedynie, czy przynajmniej jedna metoda różni się
od pozostałych; dopiero testy post-hoc pozwalają wskazać, które pary metod różnią się
istotnie. Jednostką analizy jest zagregowany wynik pojedynczego powtórzenia pomiaru
(mediana opóźnienia danego przebiegu), a wartości odstające odrzucane są metodą rozstępu
międzykwartylowego. Takie podejście pozwala formułować wnioski o przewadze jednej metody nad
inną z określonym poziomem ufności, a nie wyłącznie na podstawie porównania surowych
wartości średnich.
