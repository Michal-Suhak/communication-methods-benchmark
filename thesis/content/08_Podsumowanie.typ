#import "../utils.typ": todo, silentheading, flex-caption

= Podsumowanie <podsumowanie>

Niniejsza praca magisterska poświęcona była porównaniu wydajności pięciu reprezentatywnych
metod komunikacji stosowanych w systemach rozproszonych: REST, gRPC, GraphQL, AMQP oraz
Apache Kafka. Głównym celem pracy było przeprowadzenie rzetelnego i powtarzalnego porównania
empirycznego, którego wyniki mogłyby stanowić praktyczne wsparcie dla architektów
oprogramowania na etapie projektowania systemów.

W części teoretycznej dokonano przeglądu literatury oraz osadzono problematykę w kontekście
fundamentalnych pojęć systemów rozproszonych, w tym twierdzeń CAP i PACELC oraz wzorców
komunikacji synchronicznej i asynchronicznej. Następnie szczegółowo omówiono techniczną
charakterystykę każdej z badanych metod, wskazując ich mocne strony oraz ograniczenia. W
części praktycznej zaprojektowano i zaimplementowano w pełni skonteneryzowane środowisko
testowe zapewniające powtarzalność i izolację eksperymentów, a także zdefiniowano spójną
metodologię pomiarów obejmującą cztery scenariusze testowe oraz precyzyjnie określony zestaw
metryk.

Najważniejszym wynikiem empirycznym pracy jest wykazanie zdecydowanej przewagi gRPC. Jako
jedyna spośród badanych metod nie uległ on nasyceniu, utrzymując medianę opóźnienia poniżej
trzech milisekund nawet przy dwóch tysiącach równoczesnych użytkowników, podczas gdy REST
i GraphQL uległy nasyceniu już między stu a pięciuset użytkownikami, a ich opóźnienie wzrosło
o dwa do trzech rzędów wielkości. Metody asynchroniczne AMQP i Apache Kafka wykazały odmienną charakterystykę,
kładąc nacisk na przepustowość i trwałość kosztem wyższego opóźnienia publikacji; w teście
długotrwałym wszystkie pięć metod zachowało pełną stabilność, bez oznak degradacji w czasie.

Poza samym porównaniem wydajnościowym praca wniosła dwa elementy wzmacniające wiarygodność
i kompletność wniosków. Po pierwsze, zastosowano jednolitą, powtarzalną procedurę pomiarową
oraz dwustopniową analizę istotności statystycznej, dzięki czemu obserwowane różnice między
metodami potwierdzono z określonym poziomem ufności, a nie wyłącznie na podstawie surowych
wartości średnich. Po drugie, w przypadku metod asynchronicznych zweryfikowano
eksperymentalnie ich zdolność do zachowania kompletu wiadomości mimo awarii konsumenta oraz
ograniczoną latencję na pełnej ścieżce dostarczania — właściwości, których model
żądanie–odpowiedź nie zapewnia, a które odróżniają komunikację asynchroniczną w sposób
wykraczający poza samą charakterystykę opóźnień i przepustowości.

Zrealizowanie wszystkich założonych celów badawczych pozwoliło na sformułowanie praktycznej
macierzy decyzyjnej, która stanowi syntetyczne zestawienie rekomendacji dotyczących wyboru
metody komunikacji w zależności od priorytetów projektu. Wkład pracy polega zarówno na
dostarczeniu jednolitego porównania obejmującego jednocześnie metody synchroniczne i
asynchroniczne, jak i na udostępnieniu odtwarzalnego środowiska testowego, które może
posłużyć jako podstawa dalszych badań.

Praktyczna wartość uzyskanych wyników wynika z możliwości ich bezpośredniego wykorzystania
przy podejmowaniu decyzji architektonicznych. Zamiast opierać wybór protokołu na intuicji lub
popularności technologii, projektant może odwołać się do obiektywnych kryteriów wynikających
z pomiarów przeprowadzonych w porównywalnych warunkach. Wśród wyzwań napotkanych podczas
realizacji pracy na pierwszy plan wysunęło się zapewnienie pełnej porównywalności
implementacji oraz eliminacja czynników zakłócających pomiary, co okazało się kluczowe dla
jakości i wiarygodności wyników.

Wskazane w pracy kierunki dalszych badań — rozszerzenie na środowisko rozproszone,
uwzględnienie szyfrowania oraz objęcie analizą kolejnych protokołów — wyznaczają perspektywę
kontynuacji podjętej tematyki.
