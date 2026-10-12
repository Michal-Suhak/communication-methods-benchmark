#import "../utils.typ": todo, silentheading, flex-caption, placeholder

= Dyskusja i wnioski <dyskusja>

Rozdział siódmy łączy wyniki badań przedstawione w rozdziale szóstym i formułuje praktyczne
wnioski oraz rekomendacje dla projektantów systemów rozproszonych. Uzyskane wyniki odniesiono
do celów pracy oraz do ustaleń dostępnych w literaturze, oceniając stopień ich realizacji
oraz zgodność z oczekiwaniami.

== Podsumowanie wyników

Na podstawie przeprowadzonych eksperymentów można sformułować syntetyczne podsumowanie
charakterystyki poszczególnych metod komunikacji, potwierdzone testami istotności
statystycznej na każdym poziomie obciążenia.

Najwyraźniejszym wynikiem badania jest zdecydowana przewaga gRPC, zgodna z oczekiwaniami
wynikającymi z literatury @Abeywickrama2017, lecz silniejsza, niż można było przypuszczać.
gRPC nie tylko osiągnął najniższe opóźnienie we wszystkich scenariuszach (mediana poniżej
1 ms dla małych wiadomości), lecz jako jedyna metoda nie uległ nasyceniu — jego mediana
opóźnienia pozostała na poziomie kilku milisekund, a p99 poniżej 10 ms nawet przy 2000
równoczesnych użytkowników, podczas gdy mediany pozostałych metod sięgnęły w tych warunkach
od 0,7 do 2,1 sekundy, a ich percentyle 99 — od 3,8 do 60 sekund. Wynik ten potwierdza
teoretyczną przewagę binarnej serializacji Protocol Buffers oraz
multipleksowania strumieni HTTP/2. Należy przy tym odnotować, że przewaga gRPC nad REST
osiąga próg istotności statystycznej dopiero od 500 równoczesnych użytkowników (podrozdział
6.1), ujawnia się zatem jako zjawisko obciążeniowe.

REST i GraphQL wykazały wyraźne nasycenie już między 100 a 500 równoczesnymi użytkownikami.
Mediana opóźnienia REST wzrosła w tym przedziale z 21 do 1080 ms i osiągnęła 1300 ms przy
1000 użytkownikach; mediana GraphQL zatrzymała się na 800 ms, lecz jego percentyl 99 sięgnął
63 sekund, a pod obciążeniem szczytowym — 60 sekund. Zachowanie to jest bezpośrednią konsekwencją przyjętej dla
zachowania porównywalności konfiguracji pojedynczego procesu roboczego serwera aplikacyjnego,
ograniczonego dodatkowo przez globalną blokadę interpretera Pythona (omówienie w podrozdziale
7.3). GraphQL okazał się konsekwentnie wolniejszy od REST ze względu na dodatkowy narzut
parsowania i walidacji zapytania.

Metody asynchroniczne wykazały odmienną charakterystykę. AMQP zapewnił bardzo niskie
opóźnienie publikacji i najwyższą przepustowość spośród metod asynchronicznych na każdym
poziomie obciążenia — do 1186 wiadomości na sekundę przy 100 użytkownikach wobec 280 dla
Kafki — degradując się dopiero przy najwyższych poziomach. Kafka
charakteryzowała się konsekwentnie wyższym opóźnieniem publikacji oraz najniższą
przepustowością spośród metod asynchronicznych, co wynikało z narzutu batchowania i pełnego
potwierdzenia zapisu (`acks=all`). Wynik ten wymaga jednak istotnego zastrzeżenia: niska przepustowość Kafki jest
konsekwencją synchronicznego trybu pomiaru przyjętego dla porównywalności latencji, który
w praktyce neutralizuje asynchroniczne batchowanie — mechanizm będący źródłem przepustowości
Kafki. Pomiar w
trybie natywnym (podrozdział 6.7) wykazał przepustowość niemal dwudziestoczterokrotnie wyższą,
co pokazuje, że wysoka przepustowość przypisywana Kafce odnosi się do trybu wsadowego, nie zaś
do synchronicznej publikacji z potwierdzeniem pojedynczych wiadomości. Wyższe opóźnienie
jednostkowe Kafki jest natomiast ceną płaconą za trwałość logu i gwarancje dostarczenia. Należy przy tym pamiętać, że opóźnienia obu metod asynchronicznych
odnoszą się do publikacji do brokera, a nie do pełnego cyklu żądanie–odpowiedź, i nie są
wprost porównywalne z metodami synchronicznymi (podrozdział 5.2). W scenariuszu długotrwałym
wszystkie metody zachowały pełną stabilność, bez oznak wycieków zasobów czy degradacji
w czasie.

Analiza latencji koniec–koniec (podrozdział 6.6) uzupełnia ten obraz o perspektywę pełnego
potoku dostarczania. Dla AMQP czas od publikacji do odebrania przez konsumenta pozostawał
bliski samej latencji publikacji, co oznacza, że konsument nadążał z odbiorem i kolejka nie
narastała; dla Kafki latencja ta była wyraźnie wyższa, lecz przez cały czas ograniczona.
Obserwacja ta ma znaczenie metodologiczne: dowodzi, że pomiar publikacji z potwierdzeniem,
choć nie obejmuje całej ścieżki dostarczania, nie zniekształca porównania przez pominięcie
narastającego buforowania wiadomości.

Uzyskane wyniki pozostają w zgodzie z ogólnymi ustaleniami literatury, wnosząc jednocześnie
ich ilościowe potwierdzenie w jednolitych warunkach. Przewaga gRPC nad REST, sygnalizowana
w badaniach nad narzutem komunikacyjnym mikroserwisów @Abeywickrama2017, okazała się nie tylko
powtarzalna, lecz silniejsza, niż mogłyby sugerować porównania ograniczone do umiarkowanego
obciążenia. Odmienny profil metod asynchronicznych — niskie opóźnienie publikacji przy
ograniczonej przepustowości w trybie synchronicznym i wysokiej w trybie wsadowym — odpowiada
natomiast teoretycznemu rozróżnieniu między modelem kolejki a modelem trwałego logu
@Narkhede2017 @Kleppmann2017.

== Odpowiedzi na pytania badawcze

Zebrane wyniki pozwalają udzielić bezpośrednich odpowiedzi na pytania badawcze postawione w
podrozdziale 1.2.

W odpowiedzi na pierwsze pytanie wykazano, że opóźnienie oraz przepustowość silnie zależą od
wyboru metody, a różnice te są istotne statystycznie na każdym poziomie obciążenia (test
Kruskala–Wallisa, p < 0,001; rozmiar efektu ε² ≈ 0,50). gRPC utrzymuje najniższe opóźnienie
w całym badanym zakresie, REST i GraphQL ulegają nasyceniu między stu a pięciuset
użytkownikami, a najwyższą przepustowość publikacji osiąga AMQP (podrozdziały 6.1–6.2).

W odpowiedzi na drugie pytanie stwierdzono, że pod obciążeniem szczytowym metody synchroniczne
oraz kolejkowe narastają do wysokiego, utrzymującego się opóźnienia (percentyl 99 rzędu
kilkudziesięciu sekund dla REST i GraphQL), lecz bez utraty żądań, podczas gdy gRPC nie ulega
nasyceniu; w teście długotrwałym wszystkie metody zachowały stabilność, bez dryfu opóźnienia
i bez błędów przez całe pięć minut (podrozdziały 6.3–6.4).

Trzecie pytanie znajduje odpowiedź w odmiennych profilach zasobowych: serwery synchroniczne są
ograniczone przez procesor (do 100% jednego rdzenia) przy niewielkim zużyciu pamięci, natomiast
brokery asynchroniczne zużywają niewiele procesora, lecz znacznie więcej pamięci (do 1024 MiB
dla Kafki); najniższy koszt procesorowy i pamięciowy wśród serwerów synchronicznych wykazał
gRPC (podrozdział 6.5).

W odpowiedzi na czwarte pytanie potwierdzono eksperymentalnie, że obie metody asynchroniczne
zachowują komplet wiadomości mimo awarii konsumenta (zerowa utrata) oraz utrzymują ograniczoną
latencję na pełnej ścieżce dostarczania — gwarancje, których model żądanie–odpowiedź nie
zapewnia, ponieważ awaria serwera w trakcie obsługi żądania oznacza jego utratę i błąd po
stronie klienta (podrozdziały 6.6–6.8).

== Macierz decyzyjna

Głównym praktycznym rezultatem pracy jest macierz decyzyjna ułatwiająca projektantom systemów
wybór odpowiedniej metody komunikacji na podstawie konkretnych wymagań. Macierz zestawia
badane metody z typowymi kryteriami wyboru oraz wskazuje rekomendowane zastosowania.

#figure(
  table(
    columns: (1.2fr, 1.6fr, 1.6fr, 1.6fr),
    align: left + horizon,
    table.header(
      [*Metoda*], [*Mocne strony*], [*Ograniczenia*], [*Rekomendowane zastosowanie*],
    ),
    [REST/HTTP],
    [Powszechność, prostota, interoperacyjność],
    [Narzut JSON, brak natywnego strumieniowania],
    [Publiczne API, integracje zewnętrzne],

    [gRPC],
    [Niskie opóźnienie, wysoka przepustowość, strumieniowanie],
    [Mniejsza czytelność, słabsze wsparcie w przeglądarkach],
    [Wewnętrzna komunikacja mikroserwisów],

    [GraphQL],
    [Elastyczność zapytań, brak nadmiarowych danych],
    [Złożoność serwera, problem N+1],
    [Złożone API klienckie, agregacja danych],

    [AMQP (RabbitMQ)],
    [Rozprzęgnięcie, gwarancje dostarczenia, routing],
    [Broker jako potencjalne wąskie gardło],
    [Zadania asynchroniczne, kolejkowanie poleceń],

    [Apache Kafka],
    [Bardzo wysoka przepustowość, trwałość logu],
    [Złożoność operacyjna, wyższe opóźnienie jednostkowe],
    [Strumieniowanie zdarzeń, event sourcing],
  ),
  caption: [Macierz decyzyjna wyboru metody komunikacji],
)<tab-macierz>

Na podstawie przeprowadzonych badań można sformułować następujące rekomendacje ogólne. gRPC
stanowi optymalny wybór dla wewnętrznej komunikacji między mikroserwisami przy wysokiej
przepustowości i niewielkich ładunkach. REST pozostaje najlepszym wyborem dla publicznych
interfejsów programistycznych ze względu na powszechną dostępność klientów oraz prostotę
integracji. Apache Kafka jest szczególnie dobrze dopasowana do scenariuszy wymagających
trwałości strumienia
zdarzeń oraz przetwarzania asynchronicznego o wysokiej przepustowości, natomiast AMQP
sprawdza się w zadaniach wymagających elastycznego routingu i niezawodnego kolejkowania
poleceń. Zdolność obu metod asynchronicznych do zachowania kompletu wiadomości mimo awarii
konsumenta została przy tym potwierdzona eksperymentalnie (podrozdział 6.8), co odróżnia je
zasadniczo od metod synchronicznych. GraphQL warto rozważyć tam, gdzie różnorodni klienci
potrzebują precyzyjnej kontroli nad strukturą pobieranych danych.

Praktyczne zastosowanie macierzy polega na uszeregowaniu wymagań projektu i dopasowaniu do nich
metody. Jeżeli priorytetem jest minimalne opóźnienie oraz wysoka przepustowość wewnętrznej
komunikacji o niewielkich ładunkach, wyniki jednoznacznie wskazują gRPC. Gdy nadrzędna jest
interoperacyjność i łatwość integracji z różnorodnymi, często zewnętrznymi klientami, właściwym
wyborem pozostaje REST, mimo wyższego narzutu formatu tekstowego. Jeżeli kluczowa jest trwałość
strumienia zdarzeń oraz możliwość ich wielokrotnego odczytu, naturalnym kandydatem jest Apache
Kafka; gdy natomiast najważniejsze są elastyczny routing i niezawodne kolejkowanie zadań bez
konieczności zachowywania pełnej historii, lepiej sprawdza się AMQP. GraphQL należy rozważać
wtedy, gdy decydującym kryterium jest ograniczenie ilości przesyłanych danych przy
zróżnicowanych potrzebach klientów — jego zmierzona zdolność do redukcji rozmiaru odpowiedzi
(podrozdział 6.2) jest tu rozstrzygająca, mimo wyższego opóźnienia jednostkowego. W projektach
o mieszanych wymaganiach typowym rozwiązaniem jest łączenie metod — na przykład gRPC w
komunikacji wewnętrznej, REST na brzegu systemu oraz broker wiadomości do zadań asynchronicznych
— dla którego niniejsza macierz stanowi uporządkowany punkt wyjścia.

== Ograniczenia badania i kierunki dalszych prac

Przeprowadzone badanie, mimo dążenia do rzetelności i powtarzalności, obarczone jest pewnymi
ograniczeniami metodologicznymi, których świadomość jest istotna dla właściwej interpretacji
wyników. Ograniczenia te można uporządkować według trzech wymiarów trafności badania
empirycznego. Trafność wewnętrzna — czy obserwowane różnice wynikają z badanych metod, a nie
z czynników ubocznych — jest ograniczona przez przyjętą konfigurację pojedynczego procesu
roboczego, globalną blokadę interpretera oraz asymetrię modelu współbieżności (pula wątków
serwera gRPC wobec pojedynczego workera metod opartych na FastAPI). Trafność zewnętrzna —
zakres uogólnienia wyników — ograniczona jest do ekosystemu języka Python, pojedynczej maszyny
oraz sieci mostkowej Dockera, z pominięciem rozproszenia geograficznego i szyfrowania
transmisji. Trafność konstruktu — czy metryki mierzą zamierzone wielkości — wymaga
uwzględnienia odmiennej semantyki opóźnienia metod asynchronicznych (publikacja z
potwierdzeniem wobec pełnego cyklu żądanie–odpowiedź) oraz możliwego ograniczenia obserwowanej
przepustowości przez sam generator obciążenia. Poszczególne ograniczenia omówiono szczegółowo
poniżej.

Po pierwsze, wszystkie eksperymenty przeprowadzono na pojedynczej maszynie, w
obrębie jednej sieci mostkowej, co eliminuje wpływ opóźnień sieci rozległej oraz rzeczywistego
rozproszenia geograficznego usług. Po drugie, implementacje wykonano w jednym języku
programowania (Python), przez co wyniki mogą nie być w pełni reprezentatywne dla implementacji
w innych ekosystemach; w szczególności globalna blokada interpretera (ang. _Global Interpreter
Lock_) ogranicza równoległość obliczeniową i wpływa na zachowanie serwerów pod obciążeniem.
Po trzecie, serwery metod synchronicznych uruchomiono w pojedynczym procesie roboczym — decyzja
ta, przyjęta świadomie dla zachowania porównywalności, oznacza jednocześnie, że zaobserwowane
nasycenie REST i GraphQL odzwierciedla wydajność jednego procesu, a nie górną granicę
możliwości tych protokołów przy skalowaniu poziomym. Po czwarte, porównanie ma charakter
zestawienia ekosystemów protokołów w typowej postaci wdrożeniowej, a nie identycznych
konfiguracji serwera: serwer gRPC wykorzystuje pulę dziesięciu wątków roboczych, podczas gdy
serwery REST i GraphQL działają w modelu asynchronicznym pojedynczego workera — różnica ta
jest nieodłączną cechą typowej postaci wdrożeniowej porównywanych technologii, lecz oznacza
też, że część obserwowanej odporności gRPC na nasycenie wynika z blisko dziesięciokrotnie
większej równoległości obsługi, a nie wyłącznie z samego protokołu. Po piąte, przy
najwyższych poziomach obciążenia górnym ograniczeniem przepustowości metod najszybszych mógł
być sam generator obciążenia działający w pojedynczym procesie, dlatego wnioski dotyczące
zachowania pod przeciążeniem opierano przede wszystkim na opóźnieniu i odsetku błędów, a nie na
surowej przepustowości. Po szóste, badanie nie obejmowało aspektów bezpieczeństwa, takich jak
szyfrowanie transmisji, które wprowadza dodatkowy narzut wydajnościowy. Po siódme, przebieg
opóźnienia Kafki w funkcji obciążenia okazał się niemonotoniczny — mediana przy 500
użytkownikach była wyższa niż przy 1000 (podrozdział 6.1) — czego nie udało się rozstrzygnąć
w ramach niniejszego badania; wyjaśnienie tego zachowania wymaga osobnego eksperymentu z
kontrolowanym rozmiarem partii wiadomości.

Wskazane ograniczenia wyznaczają jednocześnie naturalne kierunki dalszych prac. Wartościowym
rozszerzeniem byłoby powtórzenie eksperymentów w środowisku rozproszonym na wielu maszynach,
z uwzględnieniem realistycznych opóźnień sieciowych, a także zbadanie wpływu szyfrowania na
poszczególne metody. Interesującym kierunkiem jest również rozszerzenie zakresu badania o
dodatkowe metody komunikacji, takie jak protokół MQTT czy nowsze rozwiązania oparte na
protokole QUIC i HTTP/3, oraz o porównanie implementacji w różnych językach programowania.
