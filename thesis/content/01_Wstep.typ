#import "../utils.typ": todo, silentheading, flex-caption

= Wstęp <wstep>

Współczesne systemy informatyczne coraz rzadziej budowane są jako pojedyncze,
monolityczne aplikacje uruchamiane na jednej maszynie. Dominującym podejściem stało się
projektowanie systemów rozproszonych, w których funkcjonalność rozdzielona jest pomiędzy
wiele niezależnych usług komunikujących się ze sobą przez sieć. Przejście od architektury
monolitycznej do architektur mikroserwisowych oraz bezserwerowych przyniosło istotne
korzyści w zakresie skalowalności, niezależnego wdrażania komponentów oraz odporności na
awarie, lecz jednocześnie przeniosło ciężar złożoności z wnętrza pojedynczego procesu na
warstwę komunikacji międzyusługowej @Newman2019.

W systemie monolitycznym wywołanie metody odbywa się w obrębie tej samej przestrzeni
adresowej i jest praktycznie natychmiastowe. W systemie rozproszonym to samo wywołanie
wymaga serializacji danych, przesłania ich przez sieć, deserializacji po stronie odbiorcy
oraz obsługi sytuacji wyjątkowych, takich jak utrata połączenia, przekroczenie czasu
odpowiedzi czy częściowa awaria. W rezultacie sposób, w jaki usługi się komunikują,
przestaje być szczegółem implementacyjnym, a staje się jedną z najważniejszych decyzji
architektonicznych wpływających na wydajność, niezawodność i koszty utrzymania całego
systemu.

Inżynierowie oprogramowania i architekci systemów dysponują obecnie szerokim wachlarzem
protokołów i wzorców komunikacji. Z jednej strony występują metody synchroniczne oparte na
modelu żądanie–odpowiedź, takie jak REST nad protokołem HTTP, zdalne wywołania procedur
realizowane przez gRPC czy elastyczny język zapytań GraphQL. Z drugiej strony dostępne są
metody asynchroniczne oparte na pośrednikach wiadomości, reprezentowane przez protokół AMQP
wraz z brokerem RabbitMQ oraz platformę strumieniowania zdarzeń Apache Kafka. Każda z tych
metod cechuje się odmiennym modelem działania, formatem serializacji, gwarancjami
dostarczania oraz charakterystyką wydajnościową @Mitra2019.

Problem badawczy podjęty w niniejszej pracy wynika z obserwacji, że wybór metody
komunikacji w praktyce inżynierskiej jest często dokonywany w sposób intuicyjny lub na
podstawie popularności danej technologii, a nie na podstawie obiektywnych, powtarzalnych
pomiarów wydajności wykonanych w porównywalnych warunkach. Dostępne w literaturze badania
porównawcze często ograniczają się do wybranych par protokołów lub pojedynczych scenariuszy
obciążenia, co utrudnia formułowanie ogólnych wniosków. Niniejsza praca podejmuje próbę
wypełnienia tej luki poprzez systematyczne, jednolite porównanie pięciu reprezentatywnych
metod komunikacji w kontrolowanym środowisku testowym.

== Cel i zakres pracy

Celem niniejszej pracy magisterskiej jest przeprowadzenie rzetelnego i powtarzalnego
porównania wydajnościowego wybranych metod komunikacji stosowanych w systemach
rozproszonych. Porównanie ma charakter empiryczny — opiera się na serii eksperymentów
pomiarowych przeprowadzonych w kontrolowanym środowisku testowym, w którym wszystkie metody
są testowane w jednakowych warunkach sprzętowych, sieciowych i obciążeniowych.

Badania obejmują zarówno metody synchroniczne, oparte na modelu żądanie–odpowiedź, jak
i metody asynchroniczne, oparte na kolejkowaniu i strumieniowaniu wiadomości. Zakres pracy
obejmuje pięć metod komunikacji:

+ *REST nad protokołem HTTP* — jako reprezentant powszechnie stosowanej komunikacji
  synchronicznej opartej na formacie tekstowym JSON;
+ *gRPC* — jako reprezentant binarnej, wysokowydajnej komunikacji typu zdalne wywołanie
  procedury opartej na Protocol Buffers i protokole HTTP/2;
+ *GraphQL* — jako reprezentant elastycznego języka zapytań pozwalającego klientowi
  precyzyjnie określić strukturę żądanych danych;
+ *AMQP z brokerem RabbitMQ* — jako reprezentant asynchronicznej komunikacji opartej na
  kolejkach wiadomości;
+ *Apache Kafka* — jako reprezentant platformy strumieniowania zdarzeń opartej na trwałym,
  partycjonowanym logu.

W ramach pracy mierzone są trzy główne grupy metryk wydajnościowych: opóźnienie (ang.
_latency_) wyrażone w percentylach p50, p95 i p99, przepustowość (ang. _throughput_)
wyrażona w liczbie obsłużonych żądań lub wiadomości na sekundę, oraz zużycie zasobów
systemowych obejmujące obciążenie procesora i wykorzystanie pamięci operacyjnej. Dodatkowo
analizowany jest narzut związany z serializacją i deserializacją danych oraz rozmiar
serializowanego ładunku.

Poza zakresem pracy pozostają zagadnienia bezpieczeństwa komunikacji (szyfrowanie,
uwierzytelnianie, autoryzacja), aspekty związane z geograficznym rozproszeniem usług w
sieci rozległej oraz porównanie konkretnych komercyjnych implementacji brokerów i serwerów
aplikacyjnych. Praca koncentruje się na wydajnościowej charakterystyce samych metod
komunikacji w kontrolowanych, izolowanych warunkach laboratoryjnych.

== Pytania badawcze

Realizacja powyższego celu wymaga udzielenia odpowiedzi na następujące pytania badawcze:

+ Jak kształtują się opóźnienie oraz przepustowość poszczególnych metod komunikacji w funkcji
  rosnącego obciążenia i czy zaobserwowane różnice są istotne statystycznie?
+ W jaki sposób badane metody reagują na nagłe obciążenie szczytowe oraz czy zachowują
  stabilność wydajności w wydłużonym horyzoncie czasowym?
+ Jaki jest koszt zasobowy — obciążenie procesora oraz zużycie pamięci operacyjnej — każdej
  z badanych metod przy porównywalnym obciążeniu?
+ Jakie gwarancje niezawodności, w szczególności trwałość oraz odporność na awarię odbiorcy,
  oferują metody asynchroniczne i czym różnią się one pod tym względem od modelu
  żądanie–odpowiedź?

Odpowiedzi na powyższe pytania sformułowano na podstawie wyników eksperymentów przedstawionych
w rozdziale szóstym oraz ich dyskusji w rozdziale siódmym.

== Oczekiwany rezultat

Oczekiwanym rezultatem pracy jest praktyczny przewodnik pomagający projektantom systemów w
wyborze optymalnej metody komunikacji na podstawie zdefiniowanych kryteriów. Rezultat ten
zostanie przedstawiony w postaci tabeli — macierzy decyzyjnej — wraz z opisem,
uwzględniającej mierzone metryki oraz typowe scenariusze użycia.

Macierz decyzyjna ma odpowiadać na pytanie, którą metodę komunikacji warto wybrać w
zależności od priorytetów projektu: czy kluczowa jest minimalna latencja, maksymalna
przepustowość, gwarancja trwałego dostarczenia wiadomości, łatwość integracji z
zewnętrznymi klientami, czy też dojrzałość i dostępność ekosystemu narzędziowego.

Drugorzędnym, lecz istotnym rezultatem pracy jest w pełni odtwarzalne środowisko testowe,
które może posłużyć jako punkt wyjścia do dalszych badań nad wydajnością komunikacji w
systemach rozproszonych.

== Struktura pracy

Praca składa się z ośmiu rozdziałów merytorycznych, poprzedzonych stroną tytułową,
streszczeniami w języku polskim i angielskim oraz spisem treści, a zakończonych
bibliografią i załącznikami.

Rozdział drugi zawiera przegląd literatury oraz teoretyczne podstawy systemów
rozproszonych, w tym omówienie kluczowych twierdzeń i wzorców komunikacji. Rozdział trzeci
stanowi szczegółowy opis techniczny pięciu badanych metod komunikacji. Rozdział czwarty
przedstawia projekt środowiska testowego wraz z uzasadnieniem przyjętych decyzji
projektowych oraz wykorzystanym stosem technologicznym. Rozdział piąty opisuje metodologię
pomiarów, scenariusze testowe oraz metody analizy statystycznej. Rozdział szósty zawiera
prezentację i analizę uzyskanych wyników badań. Rozdział siódmy formułuje dyskusję i
wnioski wraz z praktyczną macierzą decyzyjną. Rozdział ósmy stanowi syntetyczne
podsumowanie całej pracy oraz wskazuje kierunki dalszych badań.
