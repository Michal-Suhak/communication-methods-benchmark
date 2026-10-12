#{
  import "requirements.typ": wut-thesis, glossarium, drafting
  import wut-thesis: wut-thesis, acknowledgements, figure-outline, table-outline, appendix
  import "utils.typ": flex-caption-styles, todo, glossary-outline
  import "glossary.typ": glossary
  import glossarium: make-glossary, register-glossary
  import drafting: note-outline, set-margin-note-defaults

  show: make-glossary
  register-glossary(glossary)
  show: flex-caption-styles


  /** Drafting

    Zmienna "draft" włącza kolorowanie odnośników, pokazuje notatki TODO oraz napis
    DRAFT w nagłówku i na stronie tytułowej. Powinna pozostać `true` do momentu oddania
    finalnej wersji pracy.

    Zmienna "in-print" służy do wygenerowania pliku PDF do druku fizycznego (dodaje
    większy margines na oprawę i zmienia sposób numerowania). Do wersji oddawanej w APD
    należy ustawić ją na `false`.

  **/
  let draft = false
  let in-print = false
  set-margin-note-defaults(hidden: not draft)

  /// Język studiów oraz język pracy.
  let lang = (
    /// Język studiów — wpływa na język strony tytułowej.
    studies: "pl",
    /// Język pracy — wpływa na resztę tekstu (kolejność streszczeń, podpisy/odnośniki,
    /// dzielenie wyrazów itd.). Ta praca jest napisana po polsku.
    thesis: "pl",
  )

  show: wut-thesis.with(
    draft: draft,
    in-print: in-print,
    lang: lang,
    titlepage-info: (
      thesis-type: "master",
      program: "Informatyka",
      specialisation: "Inżynieria Oprogramowania",
      institute: "Instytut Informatyki",
      supervisor: "dr inż. Jarosław Wilk",
      advisor: none,
      faculty: "weiti", // Wydział Elektroniki i Technik Informacyjnych
      index-number: "340974",
      date: datetime(year: 2026, month: 10, day: 11),
    ),
    author: "Michał Suhak",
    title: (
      pl: "Porównanie wydajności wybranych metod komunikacji w systemach rozproszonych",
      en: "Performance comparison of selected communication methods in distributed systems",
    ),
    abstract: (
      pl: [
        Niniejsza praca magisterska poświęcona jest porównaniu wydajności wybranych metod
        komunikacji stosowanych w systemach rozproszonych. W obliczu rosnącej popularności
        architektur mikroserwisowych oraz systemów działających w chmurze obliczeniowej
        wybór odpowiedniego protokołu i wzorca komunikacji ma kluczowe znaczenie dla
        przepustowości, opóźnień oraz skalowalności całego systemu. Niewłaściwa decyzja na
        etapie projektowania architektury może prowadzić do trudnych do usunięcia wąskich
        gardeł wydajnościowych, nadmiernego zużycia zasobów oraz problemów ze skalowaniem
        horyzontalnym.

        W pracy dokonano przeglądu i klasyfikacji współczesnych metod komunikacji, w tym
        protokołów REST, gRPC, GraphQL, AMQP oraz Apache Kafka. Przeprowadzono
        eksperymenty pomiarowe w kontrolowanym środowisku testowym z wykorzystaniem
        narzędzi do generowania obciążenia oraz monitorowania parametrów sieciowych
        i systemowych. Środowisko zostało w pełni skonteneryzowane, co zapewniło
        powtarzalność wyników i ich niezależność od konkretnej infrastruktury sprzętowej.
        Wyniki zostały przeanalizowane statystycznie i przedstawione w formie tabel oraz
        wykresów porównawczych, z uwzględnieniem percentyli opóźnień, przepustowości oraz
        zużycia zasobów systemowych.

        Rezultatem pracy jest rekomendacja wyboru metody komunikacji w zależności od
        charakterystyki systemu, wymagań dotyczących przepustowości i niezawodności oraz
        specyfiki przetwarzanych danych. Rekomendacja przyjmuje formę praktycznej macierzy
        decyzyjnej, która może stanowić bezpośrednie wsparcie dla architektów
        oprogramowania na etapie projektowania systemów rozproszonych.
      ],
      en: [
        This master's thesis is devoted to comparing the performance of selected
        communication methods used in distributed systems. Given the increasing popularity
        of microservice architectures and cloud-based systems, choosing the right protocol
        and communication pattern is crucial for the throughput, latency, and scalability
        of the entire system. A poor decision made at the architectural design stage may
        lead to performance bottlenecks that are difficult to remove, excessive resource
        consumption, and problems with horizontal scaling.

        The thesis presents a review and classification of modern communication methods,
        including the REST, gRPC, GraphQL, AMQP, and Apache Kafka protocols. Measurement
        experiments were conducted in a controlled test environment using load generation
        tools and network and system monitoring utilities. The environment was fully
        containerised, which ensured the reproducibility of the results and their
        independence from any specific hardware infrastructure. The results were
        statistically analysed and presented in the form of tables and comparative charts,
        taking into account latency percentiles, throughput, and system resource usage.

        The outcome of the work is a recommendation for choosing a communication method
        depending on the system characteristics, throughput and reliability requirements,
        and the nature of the processed data. The recommendation takes the form of a
        practical decision matrix that can directly support software architects at the
        stage of designing distributed systems.
      ],
    ),
    keywords: (
      pl: (
        "systemy rozproszone", "mikroserwisy", "gRPC", "REST", "Apache Kafka", "AMQP",
        "GraphQL", "komunikacja sieciowa", "wydajność", "benchmarking",
      ),
      en: (
        "distributed systems", "microservices", "gRPC", "REST", "Apache Kafka", "AMQP",
        "GraphQL", "network communication", "performance", "benchmarking",
      ),
    ),
  )

  // --- Ustawienia własne ---
  set par(justification-limits: (
    tracking: (min: -0.01em, max: 0.02em),
  ))


  // --- Rozdziały główne ---
  include "content/01_Wstep.typ"
  include "content/02_SystemyRozproszone.typ"
  include "content/03_MetodyKomunikacji.typ"
  include "content/04_SrodowiskoTestowe.typ"
  include "content/05_Metodologia.typ"
  include "content/06_Wyniki.typ"
  include "content/07_Dyskusja.typ"
  include "content/08_Podsumowanie.typ"

  // --- Bibliografia ---
  bibliography("items.bib", style: "ieee", title: "Bibliografia")

  // Wykaz skrótów.
  glossary-outline(glossary)

  // Spis rysunków.
  figure-outline(lang.thesis)

  // Spis tabel.
  table-outline(lang.thesis)

  // --- Załączniki ---
  appendix(lang.thesis, include "content/Zalaczniki.typ")

  if draft {
    set heading(numbering: none)
    note-outline(title: "TODOs")
  }
}
