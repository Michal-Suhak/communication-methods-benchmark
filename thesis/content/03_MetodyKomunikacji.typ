#import "../utils.typ": todo, silentheading, flex-caption

= Omówienie badanych metod komunikacji <metody-komunikacji>

Rozdział trzeci stanowi szczegółowy opis techniczny wszystkich metod komunikacji objętych
porównaniem. Opis każdej metody został ustrukturyzowany według jednolitego schematu
obejmującego genezę i historię, specyfikację techniczną, mechanizm serializacji danych,
obsługiwane wzorce wymiany wiadomości oraz znane ograniczenia. Takie ujednolicenie ułatwia
późniejsze zestawienie metod oraz interpretację wyników pomiarowych.

== REST/HTTP

Styl architektoniczny REST (ang. _Representational State Transfer_) został sformułowany
przez Roya Fieldinga w jego rozprawie doktorskiej @Fielding2000 jako zbiór ograniczeń
architektonicznych dla systemów sieciowych. REST nie jest protokołem, lecz stylem
architektonicznym, który w praktyce niemal zawsze realizowany jest nad protokołem HTTP.
Podstawowymi założeniami REST są: model klient–serwer, bezstanowość komunikacji, jednolity
interfejs oparty na zasobach identyfikowanych przez adresy URI oraz wykorzystanie
standardowych metod HTTP do określenia rodzaju operacji.

Semantyka metod HTTP odgrywa centralną rolę w projektowaniu interfejsów REST. Metoda GET
służy do pobierania reprezentacji zasobu i powinna być bezpieczna oraz idempotentna, metoda
POST do tworzenia nowych zasobów, metoda PUT do pełnej aktualizacji zasobu, metoda PATCH do
aktualizacji częściowej, a metoda DELETE do usuwania. Reprezentacja danych przesyłana jest
najczęściej w formacie JSON, rzadziej w formacie XML. Format JSON jest tekstowy i czytelny
dla człowieka, co ułatwia debugowanie, lecz wiąże się z istotnym narzutem na serializację
oraz większym rozmiarem ładunku w porównaniu z formatami binarnymi.

Z punktu widzenia wydajności kluczowe znaczenie ma wersja wykorzystywanego protokołu
transportowego. Protokół HTTP/1.1 cierpi na problem blokowania kolejki, w którym pojedyncze
połączenie może obsługiwać tylko jedno żądanie naraz, co wymusza otwieranie wielu
równoległych połączeń. Protokół HTTP/2, omówiony szerzej w kontekście gRPC, eliminuje ten
problem dzięki multipleksowaniu wielu strumieni w obrębie jednego połączenia oraz binarnemu
kodowaniu ramek. W niniejszej pracy REST testowany jest w konfiguracji reprezentatywnej dla
typowych publicznych interfejsów programistycznych.

== gRPC i Protocol Buffers

gRPC jest nowoczesnym frameworkiem zdalnego wywoływania procedur (ang. _Remote Procedure
Call_) opracowanym przez firmę Google i udostępnionym jako oprogramowanie o otwartym kodzie
źródłowym @Indrasiri2020. W odróżnieniu od REST, który operuje na zasobach, gRPC operuje na
usługach i metodach, co czyni go bliższym tradycyjnemu modelowi wywoływania funkcji. gRPC
opiera się na dwóch fundamentalnych technologiach: mechanizmie Protocol Buffers jako formacie
serializacji oraz protokole HTTP/2 jako warstwie transportowej.

Protocol Buffers (protobuf) to binarny, niezależny od języka format serializacji danych.
Strukturę przesyłanych komunikatów oraz interfejs usługi definiuje się w pliku o rozszerzeniu
`.proto`, na podstawie którego automatycznie generowany jest kod klienta i serwera w wybranym
języku programowania. Binarna reprezentacja danych jest znacznie bardziej zwarta niż tekstowy
JSON, a proces serializacji i deserializacji jest szybszy, co przekłada się bezpośrednio na
niższe opóźnienia oraz mniejszy narzut na procesor i sieć.

gRPC obsługuje cztery typy wywołań. Wywołanie jednostkowe (ang. _unary_) odpowiada
klasycznemu modelowi żądanie–odpowiedź. Strumieniowanie po stronie serwera pozwala serwerowi
zwrócić sekwencję odpowiedzi na pojedyncze żądanie. Strumieniowanie po stronie klienta
umożliwia klientowi przesłanie sekwencji żądań. Strumieniowanie dwukierunkowe pozwala obu
stronom niezależnie wymieniać sekwencje komunikatów w obrębie jednego połączenia. Możliwości
te wynikają bezpośrednio z multipleksowania strumieni oferowanego przez HTTP/2 @Grigorik2013
i stanowią istotną przewagę gRPC w scenariuszach wymagających ciągłej, dwukierunkowej wymiany
danych.

== GraphQL

GraphQL to język zapytań dla interfejsów programistycznych opracowany przez firmę Facebook,
którego specyfikacja jest obecnie rozwijana jako standard otwarty @GraphQLSpec2021.
Jego podstawową ideą jest umożliwienie klientowi precyzyjnego określenia struktury żądanych
danych w pojedynczym zapytaniu, co rozwiązuje dwa typowe problemy interfejsów REST:
nadmiarowe pobieranie danych (ang. _over-fetching_) oraz niewystarczające pobieranie danych
wymagające wielu żądań (ang. _under-fetching_).

W GraphQL serwer udostępnia schemat opisujący dostępne typy danych oraz powiązania między
nimi. Klient wysyła zapytanie wskazujące dokładnie te pola, które są mu potrzebne, a serwer
zwraca odpowiedź o strukturze odpowiadającej zapytaniu. Za pobranie wartości poszczególnych
pól odpowiadają funkcje nazywane resolverami. Schemat GraphQL umożliwia również mechanizm
introspekcji, dzięki któremu klient może w czasie działania odpytać serwer o jego strukturę.

Istotnym wyzwaniem wydajnościowym w GraphQL jest tak zwany problem N+1. Występuje on, gdy
resolver dla listy obiektów wykonuje osobne zapytanie do źródła danych dla każdego elementu
listy, co prowadzi do liczby zapytań rosnącej liniowo z rozmiarem wyniku. Standardowym
rozwiązaniem tego problemu jest zastosowanie wzorca grupowania i buforowania żądań, znanego
pod nazwą DataLoader, który łączy wiele indywidualnych żądań w jedno zbiorcze zapytanie. Z
perspektywy wydajności GraphQL wprowadza dodatkowy narzut związany z parsowaniem i walidacją
zapytania oraz wykonaniem resolverów, który należy uwzględnić w analizie porównawczej.

== AMQP i RabbitMQ

AMQP (ang. _Advanced Message Queuing Protocol_) to otwarty protokół komunikacji
asynchronicznej oparty na pośredniku wiadomości (ang. _message broker_). Najpopularniejszą
implementacją tego protokołu jest broker RabbitMQ. W modelu AMQP nadawca, nazywany
producentem, nie przesyła wiadomości bezpośrednio do odbiorcy, lecz publikuje ją w punkcie
wymiany (ang. _exchange_), który na podstawie zdefiniowanych reguł routingu kieruje wiadomość
do jednej lub wielu kolejek.

Model wymiany wiadomości w AMQP jest elastyczny dzięki różnym typom punktów wymiany. Punkt
wymiany typu _direct_ kieruje wiadomość do kolejki na podstawie dokładnego dopasowania klucza
routingu, typu _topic_ na podstawie dopasowania wzorca, a typu _fanout_ rozsyła wiadomość do
wszystkich powiązanych kolejek, realizując wzorzec publikacja–subskrypcja. Konsumenci
pobierają wiadomości z kolejek, przy czym każda wiadomość w danej kolejce jest dostarczana
dokładnie do jednego konsumenta, co umożliwia naturalne rozłożenie obciążenia między wiele
instancji.

AMQP zapewnia mechanizmy potwierdzania dostarczenia wiadomości. Po pomyślnym przetworzeniu
wiadomości konsument wysyła potwierdzenie, dzięki czemu broker może bezpiecznie usunąć
wiadomość z kolejki; w przypadku braku potwierdzenia wiadomość może zostać ponownie
dostarczona. Pozwala to na realizację gwarancji dostarczenia co najmniej raz (ang.
_at-least-once_). Z punktu widzenia wydajności istotne jest, że broker stanowi centralny
element pośredniczący, który może stać się wąskim gardłem przy bardzo wysokim natężeniu
ruchu, lecz jednocześnie zapewnia rozprzęgnięcie producenta i konsumenta oraz buforowanie
wiadomości w sytuacji przeciążenia.

== Apache Kafka

Apache Kafka to rozproszona platforma strumieniowania zdarzeń, która w odróżnieniu od
klasycznych brokerów kolejkowych opiera się na koncepcji trwałego, partycjonowanego logu
@Narkhede2017. Zamiast usuwać wiadomości po ich skonsumowaniu, Kafka przechowuje je przez
zdefiniowany okres retencji, co umożliwia wielokrotne odczytywanie tych samych danych przez
różnych konsumentów oraz odtwarzanie stanu od dowolnego punktu w historii.

Podstawowymi pojęciami w architekturze Kafki są temat (ang. _topic_), partycja oraz
przesunięcie (ang. _offset_). Temat stanowi logiczny kanał, do którego publikowane są
zdarzenia. Każdy temat dzielony jest na partycje, które są jednostką równoległości i
skalowalności — wiadomości w obrębie pojedynczej partycji są uporządkowane, a kolejne
wiadomości otrzymują rosnące przesunięcia jednoznacznie identyfikujące ich pozycję w logu.
Brokery Kafki przechowują partycje i obsługują żądania producentów oraz konsumentów.

Kafka realizuje model publikacja–subskrypcja za pośrednictwem grup konsumentów. Konsumenci
należący do tej samej grupy współdzielą obciążenie, przy czym każda partycja jest przypisana
dokładnie do jednego konsumenta w grupie, natomiast różne grupy konsumentów odczytują te same
dane niezależnie od siebie. Platforma oferuje konfigurowalny poziom gwarancji dostarczenia,
od _at-most-once_, przez _at-least-once_, aż po _exactly-once_ przy odpowiedniej konfiguracji
transakcji. Architektura oparta na logu sprawia, że Kafka jest szczególnie wydajna w
scenariuszach o bardzo wysokiej przepustowości oraz w zastosowaniach wymagających trwałego
zapisu strumienia zdarzeń, co czyni ją naturalnym wyborem dla wzorców _event sourcing_ i
przetwarzania strumieniowego.

== Podsumowanie porównawcze badanych metod

@tab-metody-przeglad zestawia kluczowe cechy pięciu analizowanych metod, stanowiąc syntetyczne
podsumowanie niniejszego rozdziału oraz punkt odniesienia dla interpretacji wyników
pomiarowych przedstawionych w rozdziale szóstym.

#figure(
  table(
    columns: (1.1fr, 1fr, 1.1fr, 1.2fr, 1.2fr, 0.9fr),
    align: (left + horizon, left + horizon, left + horizon, left + horizon, left + horizon, left + horizon),
    table.header(
      [*Metoda*], [*Transport*], [*Serializacja*], [*Wzorzec*], [*Gwarancja dostarczania*],
      [*Strumieniowanie*],
    ),
    [REST/HTTP], [HTTP/1.1–2], [JSON (tekstowa)], [żądanie–odpowiedź], [brak wbudowanej], [nie],
    [gRPC], [HTTP/2], [Protocol Buffers (binarna)], [żądanie–odpowiedź, strumienie],
    [na poziomie wywołania], [tak (dwukierunkowe)],
    [GraphQL], [HTTP/1.1], [JSON (tekstowa)], [żądanie–odpowiedź (zapytanie)],
    [brak wbudowanej], [subskrypcje (poza badaniem)],
    [AMQP (RabbitMQ)], [TCP / AMQP], [dowolna (w badaniu JSON)],
    [kolejka, publikacja–subskrypcja], [co najmniej raz], [nie],
    [Apache Kafka], [TCP / Kafka], [dowolna (w badaniu JSON)], [publikacja–subskrypcja (log)],
    [konfigurowalna (do exactly-once)], [tak (strumień zdarzeń)],
  ),
  caption: [Porównanie kluczowych cech badanych metod komunikacji],
)<tab-metody-przeglad>
