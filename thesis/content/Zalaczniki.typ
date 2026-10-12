#import "../utils.typ": todo, silentheading, flex-caption, placeholder

= Materiały uzupełniające <zalaczniki>

W załącznikach zebrano materiały rozszerzające główną część pracy: pełne zestawienie wyników
scenariusza obciążeniowego dla wszystkich poziomów obciążenia, informacje umożliwiające
odtworzenie środowiska i eksperymentów oraz listing ilustrujący symetryczny punkt pomiaru
latencji metod asynchronicznych.

== Pełne wyniki scenariusza obciążeniowego

Tabela w głównej części pracy (@tab-wyniki-male) przedstawia wyniki dla reprezentatywnego
poziomu 100 użytkowników. @tab-zal-skalowanie zawiera komplet wyników scenariusza
obciążeniowego dla wszystkich czterech poziomów. Wartości opóźnień wyrażone są w milisekundach,
przepustowość w żądaniach (wiadomościach) na sekundę; dane pochodzą z pliku
`results/statistical_analysis_by_level.csv` (wiersz `Aggregated`, uśrednione między
powtórzeniami).

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto),
    align: (left, right, right, right, right, right),
    table.header(
      [*Metoda*], [*Użytk.*], [*p50 [ms]*], [*p95 [ms]*], [*p99 [ms]*], [*Przep. [req/s]*],
    ),
    [REST/HTTP], [10], [2], [15], [37], [155],
    [REST/HTTP], [100], [21], [96], [336], [917],
    [REST/HTTP], [500], [1080], [1980], [27 400], [276],
    [REST/HTTP], [1000], [1300], [2240], [26 400], [211],

    [gRPC], [10], [1], [9], [16], [160],
    [gRPC], [100], [< 1], [5], [6], [1021],
    [gRPC], [500], [< 1], [6], [11], [404],
    [gRPC], [1000], [3], [6], [11], [336],

    [GraphQL], [10], [3], [18], [58], [149],
    [GraphQL], [100], [198], [390], [754], [288],
    [GraphQL], [500], [758], [1500], [48 600], [145],
    [GraphQL], [1000], [800], [49 940], [63 000], [141],

    [AMQP (RabbitMQ)], [10], [2], [11], [26], [155],
    [AMQP (RabbitMQ)], [100], [6], [42], [114], [1186],
    [AMQP (RabbitMQ)], [500], [138], [952], [1280], [828],
    [AMQP (RabbitMQ)], [1000], [1060], [2220], [3020], [442],

    [Apache Kafka], [10], [8], [36], [76], [124],
    [Apache Kafka], [100], [164], [564], [790], [280],
    [Apache Kafka], [500], [2260], [3440], [9640], [156],
    [Apache Kafka], [1000], [1166], [2180], [7940], [162],
  ),
  caption: [Pełne wyniki scenariusza obciążeniowego dla wszystkich poziomów obciążenia],
)<tab-zal-skalowanie>

Dane potwierdzają obserwacje z rozdziału szóstego: gRPC utrzymuje medianę opóźnienia na poziomie
kilku milisekund w całym zakresie obciążenia, REST i GraphQL ulegają nasyceniu między stu
a pięciuset użytkownikami (mediana i wysokie percentyle rosną o rzędy wielkości), a metody
asynchroniczne
degradują się dopiero przy najwyższych poziomach.

== Odtwarzalność środowiska

Całość środowiska jest skonteneryzowana i zdefiniowana deklaratywnie, co umożliwia odtworzenie
eksperymentów na dowolnej maszynie spełniającej minimalne wymagania zasobowe. Repozytorium
projektu zawiera:

- implementacje par serwer–klient dla pięciu metod komunikacji (`rest/`, `grpc_service/`,
  `graphql_service/`, `amqp_service/`, `kafka_service/`) oraz współdzieloną warstwę danych
  i metryk (`shared/`);
- definicję środowiska `docker-compose.yml` wraz z konfiguracją monitoringu (`monitoring/`);
- scenariusze generatora obciążenia oraz orkiestrator kampanii (`load_tests/`);
- skrypty przetwarzania i analizy wyników (`scripts/`).

Pełną kampanię pomiarową uruchamia się po zbudowaniu środowiska (`docker compose up --build`)
skryptem `load_tests/run_all_scenarios.sh`. Zebrane dane surowe (pliki CSV generatora Locust,
jeden komplet na przebieg) zapisywane są w katalogu `results/`, a następnie przetwarzane
potokiem `collect_results.py` → `analyze_results.py` → `generate_charts.py`, który produkuje
zagregowane zestawienia statystyczne oraz wykresy wykorzystane w pracy.

== Symetryczny punkt pomiaru latencji metod asynchronicznych

Kluczowe dla porównywalności było, aby obie metody asynchroniczne mierzyły tę samą operację —
czas od publikacji wiadomości do potwierdzenia jej przyjęcia przez brokera (publish→ACK).
W AMQP zapewnia to włączenie potwierdzeń publikacji (`confirm_delivery()` w metodzie
`on_start`), dzięki któremu `basic_publish` blokuje do czasu potwierdzenia; w Kafce — producent
z `acks="all"` oraz oczekiwanie na rezultat wysyłki (`future.get()`). W obu przypadkach
generowanie i serializacja danych odbywają się poza oknem pomiaru, a czas raportowany jest w
milisekundach. @lst-pomiar-async przedstawia oba punkty pomiarowe.

#figure(
  ```python
  # load_tests/locustfile_amqp.py
  def _publish(self, name, routing_key, body):
      start = time.perf_counter()
      exc = None
      try:
          self._channel.basic_publish(
              exchange=_EXCHANGE, routing_key=routing_key, body=body,
              properties=pika.BasicProperties(delivery_mode=2))
      except Exception as e:
          exc = e
      elapsed_ms = (time.perf_counter() - start) * 1000
      events.request.fire(request_type="amqp", name=name,
          response_time=elapsed_ms, response_length=len(body), exception=exc)

  # load_tests/locustfile_kafka.py
  def _produce(self, name, topic, body):
      start = time.perf_counter()
      exc = None
      try:
          self._producer.send(topic, value=body).get(timeout=30)
      except Exception as e:
          exc = e
      elapsed_ms = (time.perf_counter() - start) * 1000
      events.request.fire(request_type="kafka", name=name,
          response_time=elapsed_ms, response_length=len(body), exception=exc)
  ```,
  caption: [Symetryczny punkt pomiaru latencji publikacji (publish→ACK) dla AMQP i Kafki],
)<lst-pomiar-async>

== Pełne wyniki scenariuszy szczytowego i długotrwałego

Dla kompletności @tab-zal-scenariusze zestawia pełne wyniki scenariuszy obciążenia szczytowego
(2000 użytkowników) oraz długotrwałego (50 użytkowników przez 300 s), których reprezentatywne
wartości omówiono w podrozdziałach 6.3 i 6.4. Opóźnienia wyrażono w milisekundach,
przepustowość w żądaniach (wiadomościach) na sekundę; dane pochodzą z pliku
`results/statistical_analysis_scenarios.csv`.

#figure(
  table(
    columns: (1.3fr, 1.3fr, 0.9fr, 1fr, 1fr, 1fr, 0.9fr),
    align: (left, left, right, right, right, right, right),
    table.header(
      [*Scenariusz*], [*Metoda*], [*p50 [ms]*], [*p95 [ms]*], [*p99 [ms]*],
      [*Przep. [req/s]*], [*Błędy [%]*],
    ),
    [Szczytowy], [REST/HTTP], [1267], [56 667], [58 333], [289], [0,000],
    [Szczytowy], [gRPC], [1], [6], [9], [420], [0,000],
    [Szczytowy], [GraphQL], [707], [60 000], [60 000], [181], [0,000],
    [Szczytowy], [AMQP (RabbitMQ)], [1733], [3133], [3767], [420], [0,000],
    [Szczytowy], [Apache Kafka], [2133], [3333], [5800], [159], [0,375],
    [Długotrwały], [REST/HTTP], [4], [30], [107], [695], [0,000],
    [Długotrwały], [gRPC], [< 1], [5], [7], [767], [0,000],
    [Długotrwały], [GraphQL], [42], [107], [327], [381], [0,000],
    [Długotrwały], [AMQP (RabbitMQ)], [2], [15], [48], [751], [0,000],
    [Długotrwały], [Apache Kafka], [47], [170], [377], [313], [0,000],
  ),
  caption: [Pełne wyniki scenariuszy obciążenia szczytowego i długotrwałego],
)<tab-zal-scenariusze>
