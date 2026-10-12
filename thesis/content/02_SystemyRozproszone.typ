#import "../utils.typ": todo, silentheading, flex-caption

= Systemy rozproszone -- przegląd literatury i podstawy teoretyczne <systemy-rozproszone>

Rozdział drugi przedstawia przegląd literatury naukowej oraz technicznej dotyczącej
systemów rozproszonych, ze szczególnym uwzględnieniem aspektów komunikacyjnych. Celem
rozdziału jest osadzenie problematyki pracy w kontekście teoretycznym oraz wskazanie pojęć
i twierdzeń, które wpływają na projektowanie warstwy komunikacji między usługami.

== Definicje i klasyfikacja systemów rozproszonych

System rozproszony można zdefiniować jako zbiór niezależnych komputerów, który dla
użytkownika jawi się jako jeden spójny system @Tanenbaum2017. Kluczową cechą takiego
systemu jest brak współdzielonej pamięci oraz wspólnego zegara, w wyniku czego
współpracujące węzły mogą komunikować się wyłącznie poprzez wymianę komunikatów
przesyłanych przez sieć. Ta fundamentalna właściwość odróżnia systemy rozproszone od
systemów równoległych działających w obrębie jednej maszyny i stanowi źródło większości
wyzwań projektowych.

W literaturze wyróżnia się trzy podstawowe modele obliczeniowe opisujące zachowanie systemu
w czasie. W modelu synchronicznym przyjmuje się istnienie znanych górnych ograniczeń na
czas przetwarzania oraz czas dostarczenia komunikatu. W modelu asynchronicznym nie zakłada
się żadnych ograniczeń czasowych — komunikat może dotrzeć po dowolnie długim czasie, co czyni
ten model najtrudniejszym, lecz zarazem najbardziej realistycznym. Model częściowo
synchroniczny stanowi kompromis, w którym ograniczenia czasowe istnieją, lecz nie są z góry
znane. Wybór modelu ma istotne konsekwencje dla projektowania mechanizmów wykrywania awarii
oraz uzgadniania stanu między węzłami.

Systemy rozproszone klasyfikuje się również według kryterium spójności i dostępności
danych. Z jednej strony występują systemy o silnej spójności, w których każdy odczyt zwraca
najnowszą zapisaną wartość, z drugiej zaś systemy o spójności ostatecznej, w których stan
replik jest uzgadniany w czasie, lecz przejściowo może być rozbieżny. Ta klasyfikacja jest
bezpośrednio związana z twierdzeniem CAP, omówionym w dalszej części rozdziału, i ma istotny
wpływ na dobór metody komunikacji — systemy o spójności ostatecznej często wykorzystują
asynchroniczne wzorce oparte na zdarzeniach, podczas gdy systemy o silnej spójności częściej
opierają się na komunikacji synchronicznej.

=== Twierdzenie CAP i PACELC

Twierdzenie CAP, sformułowane przez Erica Brewera @Brewer2000, stwierdza, że system
rozproszony nie może jednocześnie gwarantować trzech właściwości: spójności (ang.
_Consistency_), dostępności (ang. _Availability_) oraz tolerancji na podział sieci (ang.
_Partition tolerance_). W praktyce, ponieważ podziały sieci są nieuniknione w rzeczywistych
systemach, projektant musi dokonać wyboru między spójnością a dostępnością w sytuacji
wystąpienia podziału.

Rozszerzeniem twierdzenia CAP jest model PACELC, który uzupełnia oryginalne sformułowanie o
analizę zachowania systemu w sytuacji braku podziału sieci. Model ten stwierdza, że w
przypadku podziału (P) system wybiera między dostępnością (A) a spójnością (C), natomiast w
sytuacji normalnej, gdy podziału nie ma (E, ang. _else_), wybór następuje między opóźnieniem
(L, ang. _latency_) a spójnością (C). Model PACELC jest szczególnie istotny z punktu
widzenia niniejszej pracy, ponieważ jawnie uwzględnia kompromis między spójnością a
opóźnieniem, który jest jedną z kluczowych metryk porównywanych metod komunikacji.

== Wzorce komunikacji w systemach rozproszonych

Komunikację w systemach rozproszonych można podzielić na dwie zasadnicze kategorie:
synchroniczną i asynchroniczną. W komunikacji synchronicznej nadawca po wysłaniu żądania
oczekuje na odpowiedź, blokując dalsze przetwarzanie do momentu jej otrzymania.
Reprezentantami tego wzorca są REST, gRPC oraz GraphQL. W komunikacji asynchronicznej
nadawca przekazuje wiadomość pośrednikowi i kontynuuje pracę, nie oczekując na natychmiastową
odpowiedź; obsługa wiadomości następuje niezależnie po stronie odbiorcy. Reprezentantami
tego wzorca są AMQP oraz Apache Kafka.

Wśród wzorców integracyjnych szczególne znaczenie mają trzy modele opisane w klasycznej
literaturze poświęconej wzorcom integracji systemów @Hohpe2003. Wzorzec żądanie–odpowiedź
(ang. _request–reply_) zakłada bezpośrednią, dwukierunkową wymianę między dwoma stronami.
Wzorzec kolejkowania wiadomości (ang. _point-to-point messaging_) zakłada, że każda
wiadomość jest dostarczana dokładnie do jednego konsumenta spośród wielu nasłuchujących na
kolejce. Wzorzec publikacja–subskrypcja (ang. _publish–subscribe_) zakłada natomiast, że
pojedyncza wiadomość jest dostarczana do wszystkich zainteresowanych subskrybentów.

Z wzorcami asynchronicznymi ściśle związane są dwie koncepcje architektoniczne istotne dla
nowoczesnych systemów rozproszonych. Pierwsza z nich, znana jako _event sourcing_, polega na
przechowywaniu stanu systemu nie jako bieżącego obrazu danych, lecz jako uporządkowanej
sekwencji zdarzeń, które do tego stanu doprowadziły. Druga, określana jako CQRS (ang.
_Command Query Responsibility Segregation_), polega na rozdzieleniu ścieżki zapisu danych od
ścieżki ich odczytu. Obie koncepcje naturalnie współgrają z platformami strumieniowania
zdarzeń, takimi jak Apache Kafka, w których trwały log zdarzeń stanowi centralny element
architektury @Kleppmann2017.

== Przegląd istniejących badań porównawczych

Zagadnienie porównania wydajności protokołów komunikacyjnych było przedmiotem licznych prac
badawczych. Wyszukiwanie literatury prowadzono z wykorzystaniem słów kluczowych obejmujących
między innymi: _distributed systems communication_, _gRPC performance_, _REST benchmarking_
oraz _message queue comparison_. Poniżej przedstawiono syntetyczny przegląd najistotniejszych
ustaleń.

Badania ilościowe nad narzutem komunikacyjnym w mikroserwisach wskazują, że protokoły binarne
oparte na HTTP/2, takie jak gRPC, osiągają niższe opóźnienia i wyższą przepustowość w
porównaniu z rozwiązaniami opartymi na REST i formacie JSON, szczególnie w scenariuszach o
wysokiej częstotliwości żądań oraz niewielkim rozmiarze ładunku @Abeywickrama2017. Przewaga
ta wynika przede wszystkim z efektywności binarnej serializacji Protocol Buffers oraz z
multipleksowania strumieni w ramach jednego połączenia HTTP/2, eliminującego problem
blokowania kolejki (ang. _head-of-line blocking_) charakterystyczny dla HTTP/1.1.

Poza samą wydajnością literatura poświęcona projektowaniu interfejsów programistycznych
@Mitra2019 zwraca uwagę, że wybór protokołu synchronicznego jest również decyzją projektową.
REST zapewnia najwyższą interoperacyjność oraz dojrzałość ekosystemu narzędziowego kosztem
narzutu formatu tekstowego, podczas gdy gRPC — dzięki kontraktowi opartemu na schemacie oraz
kodowi generowanemu z pliku `.proto` @Indrasiri2020 — sprzyja wydajnej komunikacji wewnątrz
systemu, lecz słabiej nadaje się do bezpośredniej integracji z klientami przeglądarkowymi.
Kompromis ten jest istotny dla interpretacji wyników niniejszej pracy: różnice wydajnościowe
należy rozpatrywać łącznie z kontekstem zastosowania danej metody, a nie wyłącznie w
kategoriach surowego opóźnienia czy przepustowości.

Prace poświęcone architekturze mikroserwisów @Baskarada2020 @Dragoni2017 podkreślają, że
dobór metody komunikacji nie powinien być rozpatrywany wyłącznie w kategoriach surowej
wydajności, lecz także w kontekście wymagań dotyczących luźnego powiązania komponentów,
odporności na awarie oraz złożoności operacyjnej. W szczególności asynchroniczne wzorce
oparte na pośrednikach wiadomości są wskazywane jako sposób na zwiększenie odporności systemu
poprzez rozprzęgnięcie nadawcy i odbiorcy w czasie.

Literatura poświęcona platformie Apache Kafka @Narkhede2017 oraz aplikacjom intensywnie
przetwarzającym dane @Kleppmann2017 wskazuje na fundamentalną różnicę między modelem kolejki
a modelem trwałego logu. W modelu kolejki wiadomość po skonsumowaniu jest zwykle usuwana,
podczas gdy w modelu logu zdarzenia są przechowywane przez zdefiniowany okres i mogą być
wielokrotnie odczytywane przez różnych konsumentów, co umożliwia odtwarzanie stanu oraz
implementację wzorców _event sourcing_.

Krytyczna analiza dostępnych badań prowadzi do wniosku, że wiele z nich ogranicza się do
porównania wybranych par protokołów lub pojedynczych scenariuszy obciążenia, rzadko zaś
obejmuje jednoczesne, jednolite porównanie zarówno metod synchronicznych, jak i
asynchronicznych w identycznych warunkach środowiskowych. Dodatkowym ograniczeniem części
dostępnych badań jest brak jawnej analizy istotności statystycznej — wyniki prezentowane są
niekiedy jako pojedyncze pomiary lub surowe wartości średnie, bez testów różnic między metodami
oraz bez kontroli zmienności między powtórzeniami. Stanowi to lukę badawczą, którą niniejsza
praca stara się zaadresować poprzez objęcie jednym, spójnym eksperymentem pięciu
reprezentatywnych metod komunikacji, przy wielokrotnych powtórzeniach pomiarów oraz
dwustopniowej analizie istotności statystycznej (test zbiorczy oraz testy post-hoc par).
