#import "../utils.typ": todo, silentheading, flex-caption, placeholder

= Projekt środowiska testowego <srodowisko-testowe>

Rozdział czwarty szczegółowo opisuje projekt i architekturę środowiska testowego, w którym
przeprowadzono wszystkie eksperymenty pomiarowe. Kluczowym założeniem przyjętym przy
projektowaniu środowiska była pełna powtarzalność eksperymentów oraz izolacja poszczególnych
usług, dzięki czemu wyniki pomiarów odzwierciedlają charakterystykę samych metod
komunikacji, a nie przypadkowych czynników środowiskowych.

== Architektura środowiska

Środowisko testowe zostało zbudowane przy użyciu kontenerów Docker oraz orkiestratora Docker
Compose. Konteneryzacja zapewnia niezależność wyników od konkretnej infrastruktury
sprzętowej oraz umożliwia łatwe odtworzenie całej konfiguracji na dowolnej maszynie
spełniającej minimalne wymagania zasobowe. Każdy komponent systemu — serwer danej metody
komunikacji, ewentualny broker oraz narzędzia pomocnicze — działa w osobnym kontenerze, co
zapewnia izolację zasobów i odwzorowuje realistyczne warunki wdrożenia.

Topologia środowiska obejmuje cztery główne grupy komponentów. Pierwszą stanowią kontenery
usług testowanych, czyli pary serwer–klient dla każdej z pięciu metod komunikacji. Drugą
grupę tworzą kontenery infrastruktury pośredniczącej, niezbędne dla metod asynchronicznych,
czyli broker RabbitMQ oraz broker Apache Kafka wraz z wymaganymi komponentami
towarzyszącymi. Trzecią grupą jest generator obciążenia odpowiedzialny za symulację ruchu.
Czwartą grupę stanowi stos monitorujący, zbierający i wizualizujący metryki wydajnościowe.
Wszystkie kontenery komunikują się w obrębie dedykowanej sieci wirtualnej zarządzanej przez
Docker Compose.

#figure(
  block(
    stroke: 0.5pt + luma(150),
    radius: 4pt,
    inset: 12pt,
    [
      #set text(size: 8.5pt)
      #align(center)[#text(weight: "bold")[Sieć mostkowa (bridge) Docker Compose]]
      #v(6pt)
      #align(center, rect(inset: 7pt, radius: 3pt, fill: luma(240))[
        Generator obciążenia — *Locust* \
        (klient metod synchronicznych, producent metod asynchronicznych)
      ])
      #align(center)[#text(size: 11pt)[#sym.arrow.b] \ #text(size: 7.5pt)[HTTP/1.1 · HTTP/2 · AMQP · Kafka]]
      #v(4pt)
      #grid(
        columns: (1fr, 1fr),
        column-gutter: 12pt,
        rect(inset: 7pt, radius: 3pt, width: 100%)[
          *Usługi synchroniczne* \
          serwery: REST/HTTP · gRPC · GraphQL
        ],
        rect(inset: 7pt, radius: 3pt, width: 100%)[
          *Metody asynchroniczne* \
          brokery: RabbitMQ · Kafka (+ ZooKeeper) \
          konsumenci: AMQP · Kafka
        ],
      )
      #align(center)[#text(size: 11pt)[#sym.arrow.b] \ #text(size: 7.5pt)[metryki `/metrics` — pobieranie (ang. _scrape_)]]
      #v(4pt)
      #align(center, rect(inset: 7pt, radius: 3pt, width: 100%)[
        *Stos monitorujący* — cAdvisor (metryki kontenerów) #sym.arrow.r Prometheus #sym.arrow.r Grafana
      ])
    ],
  ),
  caption: flex-caption(
    [Schemat topologii środowiska testowego],
    [Topologia środowiska testowego],
  ),
  kind: image,
)<rys-topologia>

== Specyfikacja sprzętowa i konfiguracja sieciowa

Wszystkie eksperymenty przeprowadzono na pojedynczej maszynie testowej o ustalonej,
niezmiennej konfiguracji sprzętowej, co eliminuje wpływ różnic sprzętowych na porównanie.
@tab-specyfikacja przedstawia specyfikację środowiska testowego.

#figure(
  table(
    columns: (1fr, 1fr),
    align: left + horizon,
    table.header([*Parametr*], [*Wartość*]),
    [Procesor (CPU)], [Apple M1 (8 rdzeni: 4 wydajnościowe + 4 energooszczędne)],
    [Pamięć operacyjna (RAM)], [16 GB; 12 GB przydzielone maszynie wirtualnej Dockera],
    [System operacyjny], [macOS 26.2 (kompilacja 25C56)],
    [Wersja Docker], [28.4.0],
    [Wersja Docker Compose], [v2.39.4],
    [Wersja Python (kontenery usług)], [3.12],
    [Konfiguracja sieci kontenerów], [sieć mostkowa (bridge) Docker Compose],
  ),
  caption: [Specyfikacja środowiska testowego],
)<tab-specyfikacja>

Konfiguracja sieciowa opiera się na domyślnej sieci mostkowej tworzonej przez Docker
Compose, w której kontenery komunikują się po nazwach usług rozwiązywanych przez wbudowany
serwer DNS. Takie rozwiązanie odwzorowuje typowy scenariusz komunikacji wewnątrz pojedynczego
hosta i minimalizuje wpływ czynników zewnętrznych, takich jak opóźnienia sieci rozległej,
które celowo pozostają poza zakresem badania.

== Implementacje testowe

Każda z pięciu analizowanych metod komunikacji została zaimplementowana w postaci pary
serwer–klient napisanej w języku Python w wersji 3.12. Jako podstawowy framework serwerowy dla
metod synchronicznych przyjęto FastAPI, co zapewnia spójność implementacji i pozwala na
rzetelne porównanie narzutu poszczególnych protokołów przy zachowaniu wspólnej warstwy
aplikacyjnej. Dla zachowania porównywalności wszystkie serwery realizują tę samą logikę
domenową, różniąc się wyłącznie warstwą komunikacji.

Implementacja REST wykorzystuje FastAPI do udostępnienia punktów końcowych operujących na
danych w formacie JSON. Implementacja gRPC opiera się na wygenerowanym ze schematu `.proto`
kodzie klienta i serwera oraz na bibliotece gRPC dla języka Python. Implementacja GraphQL
udostępnia schemat wraz z resolverami; dodatkowo zawiera dedykowany resolver demonstrujący
rozwiązanie problemu N+1 — pole powiązane z każdym elementem listy jest rozwiązywane przez
mechanizm DataLoader, który grupuje indywidualne odwołania z jednego żądania w pojedyncze
zbiorcze wywołanie źródła danych. Implementacja AMQP wykorzystuje broker RabbitMQ, w którym
producent publikuje wiadomości w punkcie wymiany z włączonym mechanizmem potwierdzeń
publikacji (ang. _publisher confirms_), a konsument pobiera je z kolejki i potwierdza ich
przetworzenie. Implementacja Apache Kafka obejmuje producenta publikującego zdarzenia w
temacie z pełnym potwierdzeniem zapisu (`acks=all`) oraz konsumenta należącego do grupy
konsumentów odczytującego te zdarzenia.

We wszystkich implementacjach format oraz rozmiar danych wejściowych i wyjściowych są
ujednolicone w obrębie danego scenariusza testowego, co zapewnia, że obserwowane różnice
wynikają z charakterystyki metody komunikacji, a nie z odmiennej struktury przesyłanych
danych. Mechanizmy zbierania metryk wydajnościowych zostały zintegrowane z każdą
implementacją w jednolity sposób, umożliwiając eksport danych do systemu monitorującego.

== Stack technologiczny

Dobór narzędzi tworzących stos technologiczny środowiska został podyktowany dążeniem do
powtarzalności, otwartości oraz powszechnej dostępności wykorzystywanych komponentów.
@tab-stack zestawia kluczowe elementy stosu wraz z pełnioną przez nie rolą.

#figure(
  table(
    columns: (auto, 1fr),
    align: left + horizon,
    table.header([*Narzędzie*], [*Rola w środowisku*]),
    [Python 3.12], [Język implementacji serwerów i klientów wszystkich metod],
    [FastAPI], [Framework serwerowy dla metod synchronicznych],
    [Locust], [Generowanie obciążenia i testy wydajnościowe],
    [Prometheus], [Zbieranie i przechowywanie metryk w postaci szeregów czasowych],
    [Grafana], [Wizualizacja metryk w postaci dashboardów],
    [cAdvisor], [Metryki zużycia zasobów (CPU, RAM) poszczególnych kontenerów],
    [Docker / Docker Compose], [Konteneryzacja i orkiestracja środowiska],
    [RabbitMQ], [Broker wiadomości dla metody AMQP],
    [Apache Kafka], [Platforma strumieniowania zdarzeń],
  ),
  caption: [Stos technologiczny środowiska testowego],
)<tab-stack>

Narzędzie Locust pełni rolę generatora obciążenia, umożliwiając definiowanie scenariuszy
testowych w postaci kodu w języku Python oraz stopniowe zwiększanie liczby równoczesnych
użytkowników. Prometheus odpowiada za zbieranie metryk w regularnych odstępach czasu i
przechowywanie ich w postaci szeregów czasowych, natomiast Grafana umożliwia ich wizualizację
w postaci czytelnych dashboardów. Do obserwowalności i śledzenia przebiegu żądań w systemie
rozproszonym można wykorzystać dodatkowo mechanizmy rozproszonego śledzenia @Shkuro2019
@Sigelman2010. Integracja tych narzędzi w ramach jednego, skonteneryzowanego środowiska
zapewnia spójny i powtarzalny przebieg pomiarów dla wszystkich badanych metod.

== Potok akwizycji i przetwarzania metryk

Rzetelność porównania zależy nie tylko od symetrii implementacji, lecz także od jednolitego
i obiektywnego sposobu zbierania danych. W tym celu każdy komponent pomiarowy został
zinstrumentowany w ten sam sposób, a dane gromadzone są z dwóch niezależnych źródeł.

Każdy serwer oraz konsument udostępnia metryki poprzez punkt końcowy klienta Prometheus na
dedykowanym porcie. Zbierane są: histogram opóźnienia obsługi żądania, histogram opóźnienia
koniec–koniec (po stronie konsumenta, dla metod asynchronicznych), licznik obsłużonych żądań,
histogram rozmiaru serializowanego ładunku oraz wskaźnik liczby aktywnych połączeń. Etykiety
metryk są kanoniczne i wspólne dla wszystkich metod, co umożliwia ich bezpośrednie
zestawianie. Serwer Prometheus odpytuje (ang. _scrape_) wszystkie te punkty oraz narzędzie
cAdvisor — dostarczające metryk zużycia procesora i pamięci poszczególnych kontenerów — w
stałych odstępach czasu, a dashboardy Grafana udostępniają podgląd przebiegu pomiaru w czasie
rzeczywistym.

Pomiar opiera się zatem na dwóch komplementarnych i niezależnych źródłach danych: generatorze
obciążenia Locust, rejestrującym opóźnienie oraz przepustowość po stronie klienta (w
milisekundach), a także systemie Prometheus, gromadzącym metryki po stronie serwera i
konsumenta oraz zużycie zasobów (w sekundach). Rozdzielność tych źródeł pozwala na wzajemną
weryfikację wyników, a każda konwersja jednostek jest w przetwarzaniu jawna. Po zakończeniu
przebiegu dane surowe są scalane i agregowane potokiem skryptów: wyniki generatora Locust
łączone są w jedno zestawienie, metryki Prometheus odczytywane w oknie czasowym dokładnie
pokrywającym się z właściwym pomiarem (percentyle wyznaczane funkcją `histogram_quantile`),
a całość poddawana analizie statystycznej oraz wizualizacji opisanym w rozdziale piątym.

== Napotkane trudności implementacyjne

Budowa środowiska pomiarowego ujawniła szereg trudności technicznych, których rozwiązanie
okazało się istotne dla rzetelności pomiaru. Ich omówienie stanowi praktyczną ilustrację
tezy, zgodnie z którą w systemach rozproszonych ciężar złożoności przenosi się na warstwę
komunikacji.

Pierwszą i najpoważniejszą trudnością był konflikt między asynchronicznym modelem bibliotek
klienckich a mechanizmem współbieżności generatora obciążenia. Locust wykorzystuje bibliotekę
gevent, która podmienia (ang. _monkey-patching_) standardowe mechanizmy współbieżności języka
Python, zamieniając wątki na lekkie procesy (ang. _greenlets_) działające w jednej pętli
zdarzeń. Pierwotne implementacje klientów AMQP i Kafki, oparte na bibliotekach asynchronicznych
`aio_pika` oraz `aiokafka`, nie dały się pogodzić z tym modelem — próba uruchomienia własnej
pętli zdarzeń kończyła się błędem czasu wykonania. Rozwiązaniem było zastąpienie bibliotek
asynchronicznych ich synchronicznymi odpowiednikami (`pika` oraz `kafka-python`), które
współpracują z geventem w sposób naturalny, ponieważ gevent podmienia operacje na gniazdach
sieciowych na poziomie systemowym.

Drugą trudnością, o charakterze metodologicznym, było zapewnienie, aby wszystkie protokoły
mierzyły porównywalną operację. W pierwotnej implementacji klient AMQP publikował wiadomości
bez oczekiwania na potwierdzenie brokera, w wyniku czego mierzony był jedynie czas zapisu do
lokalnego bufora gniazda — wielkość nieporównywalna z pełnym cyklem żądanie–odpowiedź metod
synchronicznych ani z potwierdzanym zapisem Kafki. Konieczne było jawne włączenie mechanizmu
potwierdzeń publikacji (ang. _publisher confirms_), dzięki czemu pomiar AMQP objął czas do
potwierdzenia przyjęcia wiadomości przez brokera, symetrycznie do konfiguracji `acks=all`
w Kafce. Rozróżnienie między latencją publikacji a pełnym cyklem round-trip zostało następnie
jawnie odzwierciedlone w metodologii (podrozdział 5.2).

Kolejnym wyzwaniem było ograniczenie wynikające z globalnej blokady interpretera Pythona
(ang. _Global Interpreter Lock_), która pozwala na wykonywanie kodu bajtowego tylko przez
jeden wątek naraz. W połączeniu z przyjętą — dla zachowania porównywalności — konfiguracją
pojedynczego procesu roboczego serwera aplikacyjnego ograniczenie to bezpośrednio wpłynęło na
obserwowane nasycenie metod synchronicznych pod wysokim obciążeniem. Jest to świadomy
kompromis: rezygnacja ze skalowania poziomego w zamian za jednorodne warunki porównania.

Istotne okazało się również zarządzanie zasobami w środowisku kontenerowym na komputerze
z systemem macOS, gdzie Docker działa wewnątrz maszyny wirtualnej. Domyślna alokacja pamięci
sterty maszyny wirtualnej Javy przez brokery oparte na tej platformie przekraczała limity
zadeklarowane dla kontenerów, prowadząc do ich awaryjnego zatrzymywania. Rozwiązaniem było
jawne ograniczenie rozmiaru sterty poprzez zmienne środowiskowe oraz zwiększenie przydziału
pamięci maszyny wirtualnej. Ponadto zaobserwowano, że pierwsze wiadomości wysyłane do nowo
utworzonego tematu Kafki cechują się podwyższonym opóźnieniem, wynikającym z procesu wyboru
lidera partycji; zjawisko to było bezpośrednim uzasadnieniem dla zastosowania fazy rozgrzewki
przed każdym pomiarem.

Ostatnią grupę trudności stanowiło zachowanie samego generatora obciążenia przy bardzo dużej
liczbie równoczesnych użytkowników. Przy jednoczesnym uruchamianiu dwóch tysięcy producentów
Kafki broker ulegał chwilowemu przeciążeniu, a przy zamykaniu testu generator zgłaszał masowe,
lecz nieszkodliwe wyjątki wewnętrzne biblioteki gevent. Przejściowe przeciążenie skutkowało
nielicznymi przekroczeniami limitu czasu wysyłki, które trafiły do właściwego okna pomiarowego
i zostały odnotowane jako odsetek błędów rzędu 0,375% w scenariuszu szczytowym (podrozdział
6.3) — jest to jedyny niezerowy odsetek błędów w całej kampanii. Masowe wyjątki wewnętrzne biblioteki gevent przy zamykaniu testu
zachodziły natomiast poza oknem pomiarowym i nie zniekształcały zapisanych wyników, co
potwierdziła spójność liczby żądań między powtórzeniami oraz zerowy odsetek błędów w
pozostałych scenariuszach i dla pozostałych metod.
