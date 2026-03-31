from __future__ import annotations

from pathlib import Path
import textwrap


PAGE_WIDTH = 595.28
PAGE_HEIGHT = 841.89
MARGIN_LEFT = 58
MARGIN_RIGHT = 58
TOP_Y = 792
BOTTOM_Y = 52
LINE_GAP = 16


def escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class SimplePdf:
    def __init__(self) -> None:
        self.pages: list[list[str]] = []
        self.current_page: list[str] = []
        self.y = TOP_Y
        self.new_page()

    def new_page(self) -> None:
        if self.current_page:
            self.pages.append(self.current_page)
        self.current_page = []
        self.y = TOP_Y

    def ensure_space(self, required: int = LINE_GAP) -> None:
        if self.y - required < BOTTOM_Y:
            self.new_page()

    def approx_text_width(self, text: str, font_size: int) -> float:
        width_factor = 0.48
        return len(text) * font_size * width_factor

    def write_line(
        self,
        text: str,
        *,
        font: str = "F1",
        size: int = 12,
        x: float = MARGIN_LEFT,
        align: str = "left",
        gap: int = LINE_GAP,
    ) -> None:
        self.ensure_space(gap)
        if align == "center":
            x = max(MARGIN_LEFT, (PAGE_WIDTH - self.approx_text_width(text, size)) / 2)
        elif align == "right":
            x = PAGE_WIDTH - MARGIN_RIGHT - self.approx_text_width(text, size)
        self.current_page.append(
            f"BT /{font} {size} Tf 1 0 0 1 {x:.2f} {self.y:.2f} Tm ({escape_pdf_text(text)}) Tj ET"
        )
        self.y -= gap

    def blank(self, lines: int = 1) -> None:
        self.y -= LINE_GAP * lines
        if self.y < BOTTOM_Y:
            self.new_page()

    def paragraph(
        self,
        text: str,
        *,
        indent: int = 0,
        font: str = "F1",
        size: int = 12,
        gap_after: int = 6,
    ) -> None:
        width = 90 if indent == 0 else 84
        wrapped = textwrap.wrap(" ".join(text.split()), width=width)
        for line in wrapped:
            self.write_line(line, font=font, size=size, x=MARGIN_LEFT + indent, gap=LINE_GAP)
        self.y -= gap_after

    def bullet_list(self, items: list[str]) -> None:
        for item in items:
            wrapped = textwrap.wrap(" ".join(item.split()), width=82)
            if not wrapped:
                continue
            self.write_line(f"- {wrapped[0]}", font="F1", size=12, x=MARGIN_LEFT + 8)
            for line in wrapped[1:]:
                self.write_line(line, font="F1", size=12, x=MARGIN_LEFT + 24)
            self.y -= 4

    def numbered_list(self, items: list[str]) -> None:
        for index, item in enumerate(items, start=1):
            wrapped = textwrap.wrap(" ".join(item.split()), width=80)
            if not wrapped:
                continue
            self.write_line(f"{index}. {wrapped[0]}", font="F1", size=12, x=MARGIN_LEFT + 8)
            for line in wrapped[1:]:
                self.write_line(line, font="F1", size=12, x=MARGIN_LEFT + 26)
            self.y -= 4

    def heading1(self, text: str) -> None:
        self.write_line(text.upper(), font="F2", size=18, align="center", gap=20)
        self.blank()

    def heading2(self, text: str) -> None:
        self.write_line(text.upper(), font="F2", size=15, x=MARGIN_LEFT, gap=18)
        self.y -= 2

    def divider(self) -> None:
        self.ensure_space(12)
        self.current_page.append(f"{MARGIN_LEFT:.2f} {self.y:.2f} m {PAGE_WIDTH - MARGIN_RIGHT:.2f} {self.y:.2f} l S")
        self.y -= 12

    def box(self, x: float, y: float, w: float, h: float) -> None:
        self.current_page.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")

    def signature_line(self, x: float, y: float, width: float, label: str) -> None:
        self.current_page.append(f"{x:.2f} {y:.2f} m {x + width:.2f} {y:.2f} l S")
        self.current_page.append(
            f"BT /F2 11 Tf 1 0 0 1 {x + 20:.2f} {y - 14:.2f} Tm ({escape_pdf_text(label)}) Tj ET"
        )

    def finish(self) -> bytes:
        if self.current_page:
            self.pages.append(self.current_page)
            self.current_page = []

        objects: list[bytes] = []

        def add_object(data: str | bytes) -> int:
            payload = data.encode("latin1") if isinstance(data, str) else data
            objects.append(payload)
            return len(objects)

        font1 = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>")
        font2 = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold >>")
        font3 = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Italic >>")

        page_ids: list[int] = []
        content_ids: list[int] = []

        for page_commands in self.pages:
            content = "\n".join(["1 w"] + page_commands) + "\n"
            content_id = add_object(
                f"<< /Length {len(content.encode('latin1'))} >>\nstream\n{content}endstream"
            )
            content_ids.append(content_id)
            page_ids.append(0)

        pages_id = add_object("<< /Type /Pages /Kids [] /Count 0 >>")

        for index, content_id in enumerate(content_ids):
            page_dict = (
                f"<< /Type /Page /Parent {pages_id} 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH:.2f} {PAGE_HEIGHT:.2f}] "
                f"/Resources << /Font << /F1 {font1} 0 R /F2 {font2} 0 R /F3 {font3} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            )
            page_ids[index] = add_object(page_dict)

        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
        objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("latin1")

        catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

        pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for idx, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{idx} 0 obj\n".encode("latin1"))
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")

        xref_start = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin1"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("latin1"))
        pdf.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
                f"startxref\n{xref_start}\n%%EOF"
            ).encode("latin1")
        )
        return bytes(pdf)


def build_report(pdf: SimplePdf) -> None:
    pdf.write_line("PROJECT REPORT", font="F2", size=14, align="center", gap=18)
    pdf.blank(3)
    pdf.write_line(
        "AI-BASED ONLINE REVIEW ANALYSIS AND BRAND REPUTATION MONITORING SYSTEM",
        font="F2",
        size=20,
        align="center",
        gap=26,
    )
    pdf.write_line(
        "BrandPulse Documentation Report in Academic Submission Format",
        font="F3",
        size=13,
        align="center",
        gap=20,
    )
    pdf.blank(3)

    pdf.box(90, 520, 415, 78)
    pdf.write_line("Submitted by", font="F2", size=13, align="center", gap=18)
    pdf.write_line("[Student Name]", align="center")
    pdf.write_line("[Register Number / Roll Number]", align="center")
    pdf.write_line("[Department / Class / Section]", align="center")

    pdf.blank(2)
    pdf.box(90, 385, 415, 78)
    pdf.write_line("Submitted to", font="F2", size=13, align="center", gap=18)
    pdf.write_line("[Guide Name]", align="center")
    pdf.write_line("[Department Name]", align="center")
    pdf.write_line("[College / Institution Name]", align="center")

    pdf.blank(3)
    pdf.write_line("Academic Year: 2025-2026", font="F2", size=12, align="center")
    pdf.write_line("Date: March 25, 2026", font="F2", size=12, align="center")
    pdf.signature_line(95, 120, 150, "Project Guide")
    pdf.signature_line(350, 120, 150, "Head of Department")

    pdf.new_page()

    pdf.heading1("Certificate")
    pdf.paragraph(
        'This is to certify that the project report entitled "AI-Based Online Review Analysis and Brand '
        'Reputation Monitoring System" is a bonafide work carried out by [Student Name] in partial '
        "fulfillment of the requirements for the relevant academic program under the guidance and supervision "
        "of [Guide Name]."
    )
    pdf.paragraph(
        "The work documented in this report has been completed during the academic year 2025-2026 and has not "
        "been submitted in full or in part to any other institution for the award of any degree, diploma, or "
        "similar academic recognition."
    )
    pdf.blank(8)
    pdf.signature_line(90, 190, 170, "Guide Signature")
    pdf.signature_line(330, 190, 170, "Department Seal / HOD")

    pdf.new_page()

    pdf.heading1("Declaration by the Student")
    pdf.paragraph(
        'I hereby declare that the project titled "AI-Based Online Review Analysis and Brand Reputation '
        'Monitoring System" is an original work prepared by me under the guidance of [Guide Name]. The report '
        "is based on my own implementation, analysis, documentation, and testing effort, except where "
        "references and conceptual sources have been properly acknowledged."
    )
    pdf.paragraph(
        "I further declare that this report has not been copied from any previously submitted project and that "
        "all external resources, datasets, and technical references used in the preparation of this "
        "documentation have been properly cited in the references section."
    )
    pdf.blank(9)
    pdf.write_line("Signature of Student", font="F2", size=12, x=360)
    pdf.write_line("[Student Name]", x=360)
    pdf.write_line("[Register Number]", x=360)

    pdf.new_page()

    pdf.heading1("Acknowledgment")
    pdf.paragraph(
        "I express my sincere gratitude to everyone who supported the successful completion of this project. "
        "I am especially thankful to [Guide Name] for the guidance, encouragement, technical direction, and "
        "valuable feedback provided throughout the development of the project."
    )
    pdf.paragraph(
        "I also extend my thanks to the Head of the Department, faculty members, and institution management "
        "for their academic support and for providing the environment and resources required to complete this "
        "work."
    )
    pdf.paragraph(
        "Finally, I thank my family, friends, and classmates for their encouragement and motivation during the "
        "implementation and documentation phases of the project."
    )

    pdf.new_page()

    pdf.heading1("Abstract")
    pdf.paragraph(
        "The AI-Based Online Review Analysis and Brand Reputation Monitoring System, developed under the project "
        "name BrandPulse, is an end-to-end review analytics platform designed to process ecommerce reviews, "
        "classify sentiment, calculate brand reputation, and present business-ready insights through an "
        "interactive dashboard. The system addresses a common business challenge: large-scale online reviews "
        "are difficult to analyze manually, especially when they arrive across multiple brands, platforms, and "
        "languages."
    )
    pdf.paragraph(
        "The project uses a Flask-based backend, a browser-based dashboard, and a machine learning pipeline "
        "built around review preprocessing, TF-IDF feature extraction, and a calibrated Logistic Regression "
        "sentiment model. In addition to standard sentiment classification, the system includes multilingual "
        "normalization for English and several Indian-language review patterns, confidence-aware prediction, "
        "batch processing, rating-mismatch detection, realtime review ingestion, connector polling, and "
        "role-based dashboards for administrators, analysts, and marketing users."
    )
    pdf.paragraph(
        "The current generated artifact snapshot reports a consolidated reputation summary over more than "
        "seven lakh processed reviews, with structured outputs such as sentiment distributions, trend files, "
        "platform summaries, prediction artifacts, and per-brand reputation scores. The project demonstrates "
        "how AI-assisted text analytics can be converted into practical brand-monitoring workflows for "
        "academic and prototype deployment use cases."
    )

    pdf.new_page()

    pdf.heading1("Table of Contents")
    pdf.numbered_list(
        [
            "Certificate",
            "Declaration by the Student",
            "Acknowledgment",
            "Abstract",
            "Chapter 1 - Introduction",
            "Chapter 2 - Literature Survey",
            "Chapter 3 - System Analysis and Requirements",
            "Chapter 4 - System Design",
            "Chapter 5 - Implementation Methodology",
            "Chapter 6 - Testing and Validation",
            "Chapter 7 - Results, Advantages, and Limitations",
            "Chapter 8 - Conclusion and Future Scope",
            "References",
        ]
    )

    pdf.new_page()

    pdf.heading1("Chapter 1 - Introduction")
    pdf.divider()
    pdf.heading2("1.1 Background")
    pdf.paragraph(
        "Modern ecommerce platforms receive a very large volume of user-generated reviews across websites, apps, "
        "and marketplaces. These reviews contain useful signals about product quality, delivery performance, "
        "customer support, and overall brand satisfaction. However, manually reading and summarizing large "
        "review collections is slow, inconsistent, and difficult to scale."
    )
    pdf.paragraph(
        "Businesses therefore require intelligent systems that can automatically process review text, identify "
        "sentiment, aggregate the results, and convert them into measurable brand-level indicators. An "
        "effective solution should also support operational realities such as multilingual content, batch "
        "processing, realtime ingestion, and role-based analytics consumption."
    )
    pdf.heading2("1.2 Problem Statement")
    pdf.paragraph(
        "Organizations with large review volumes face difficulty in understanding customer sentiment quickly and "
        "accurately. Traditional manual analysis cannot easily support thousands of reviews, multiple "
        "platforms, or mixed-language input. As a result, important signals about brand perception, product "
        "issues, and service dissatisfaction may be delayed or overlooked."
    )
    pdf.heading2("1.3 Objectives")
    pdf.bullet_list(
        [
            "To preprocess and normalize raw ecommerce review datasets from multiple input structures.",
            "To classify review sentiment automatically using a machine learning pipeline.",
            "To support multilingual review normalization for English and several Indian-language patterns.",
            "To compute brand reputation scores and supporting dashboard analytics.",
            "To provide single-review, batch-review, and realtime review analysis workflows.",
            "To support different dashboard user roles such as admin, analyst, and marketing staff.",
        ]
    )
    pdf.heading2("1.4 Scope")
    pdf.paragraph(
        "The project scope includes review ingestion, preprocessing, training, prediction, reputation scoring, "
        "dashboard presentation, role-based access, and realtime review monitoring. The project focuses on "
        "review sentiment and brand reputation analytics rather than deep aspect-based sentiment decomposition "
        "or enterprise cloud-scale deployment."
    )

    pdf.new_page()

    pdf.heading1("Chapter 2 - Literature Survey")
    pdf.divider()
    pdf.heading2("2.1 Review Analytics in Existing Research")
    pdf.paragraph(
        "Sentiment analysis has been widely studied as a natural language processing task for classifying user "
        "opinion into positive, negative, or neutral categories. Review mining is frequently applied in "
        "ecommerce, hospitality, social platforms, and mobile app ecosystems to measure customer satisfaction "
        "and detect common pain points."
    )
    pdf.heading2("2.2 Brand Monitoring Systems")
    pdf.paragraph(
        "Brand-monitoring systems often combine sentiment classification with trend dashboards, keyword "
        "extraction, and platform comparisons. Many existing tools focus on English-only data or rely heavily "
        "on costly external APIs, making them less suitable for offline academic prototypes or multilingual "
        "regional review datasets."
    )
    pdf.heading2("2.3 Research Gaps")
    pdf.bullet_list(
        [
            "Limited support for Indian-language or romanized multilingual review patterns.",
            "Lack of integrated pipelines combining training, prediction, scoring, and dashboard monitoring.",
            "Insufficient attention to confidence interpretation and rating mismatch checks.",
            "Few compact academic systems include realtime ingestion and connector-driven review polling.",
        ]
    )
    pdf.heading2("2.4 Need for the Proposed System")
    pdf.paragraph(
        "The proposed BrandPulse system addresses these gaps by integrating preprocessing, model training, "
        "confidence-aware sentiment prediction, multilingual normalization, brand score computation, dashboard "
        "analytics, and realtime ingestion into one working full-stack system."
    )

    pdf.new_page()

    pdf.heading1("Chapter 3 - System Analysis and Requirements")
    pdf.divider()
    pdf.heading2("3.1 Existing System")
    pdf.paragraph(
        "Existing manual review-analysis methods usually involve spreadsheets, manual reading, or basic keyword "
        "counts. These approaches are time-consuming, do not scale well to large datasets, and do not easily "
        "support brand-wise reputation scoring or continuous monitoring."
    )
    pdf.heading2("3.2 Proposed System")
    pdf.paragraph(
        "The proposed system provides an end-to-end workflow that accepts raw review data, preprocesses and "
        "cleans the text, trains a sentiment model, predicts sentiment for single or batch reviews, computes "
        "brand reputation, and exposes the results through an authenticated web dashboard. It also ingests "
        "realtime reviews via API and connectors for ongoing monitoring."
    )
    pdf.heading2("3.3 Functional Requirements")
    pdf.bullet_list(
        [
            "Authentication: register, log in, log out, and manage session-aware dashboard access by user role.",
            "Preprocessing: load raw CSV files, normalize schema, clean review text, and build the cleaned dataset.",
            "Training: create TF-IDF features, train calibrated sentiment models, and save metrics and artifacts.",
            "Prediction: support single-review and batch-review sentiment prediction with confidence details.",
            "Brand Scoring: aggregate predictions into overall and brand-wise reputation summaries.",
            "Realtime: ingest live reviews and connector data, score them immediately, and append them to monitoring storage.",
        ]
    )
    pdf.heading2("3.4 Non-Functional Requirements")
    pdf.bullet_list(
        [
            "Usability through a browser-based dashboard and guided workflow.",
            "Performance suitable for interactive single and batch predictions.",
            "Maintainability through backend modules and tests for core logic.",
            "Security through session-based authentication and role-based access control.",
            "Extensibility for additional brands, connectors, and language coverage.",
        ]
    )
    pdf.heading2("3.5 Feasibility")
    pdf.paragraph(
        "The system is technically feasible using Python, Flask, scikit-learn, and frontend web technologies. "
        "It is economically feasible for academic development because it relies primarily on open-source "
        "libraries and local artifacts. Operationally, it aligns with how businesses review brand perception "
        "across multiple review platforms."
    )

    pdf.new_page()

    pdf.heading1("Chapter 4 - System Design")
    pdf.divider()
    pdf.heading2("4.1 High-Level Architecture")
    pdf.bullet_list(
        [
            "Raw Review CSVs, manual text input, and realtime connectors act as input sources.",
            "The preprocessing and multilingual normalization layer standardizes review content.",
            "TF-IDF feature extraction and a calibrated Logistic Regression model perform sentiment inference.",
            "Prediction services, brand scoring, dashboard analytics, and realtime storage convert outputs into monitoring views.",
        ]
    )
    pdf.heading2("4.2 Major Modules")
    pdf.bullet_list(
        [
            "Preprocessing Module: loads raw data, normalizes fields, formats dates, cleans text, and prepares training data.",
            "Multilingual Module: detects language cues and maps multilingual or romanized phrases into normalized sentiment-friendly text.",
            "Training Module: builds TF-IDF features and selects the best Logistic Regression candidate with calibration.",
            "Prediction Service: handles single and batch inference, confidence computation, and rating mismatch logic.",
            "Brand Score Module: computes overall and per-brand reputation using weighted sentiment aggregation.",
            "Dashboard Module: presents summary, trends, keywords, platforms, brands, and realtime monitoring views.",
        ]
    )
    pdf.heading2("4.3 Supported Language Handling")
    pdf.paragraph(
        "The multilingual bridge currently supports English and lexicon-based normalization cues for Hindi, "
        "Tamil, Telugu, Malayalam, Kannada, Bengali, Marathi, Gujarati, Punjabi, and Urdu. Script detection "
        "and phrase mapping are used to convert sentiment-bearing patterns into a normalized text representation "
        "before model inference."
    )
    pdf.heading2("4.4 Reputation Score Formula")
    pdf.paragraph(
        "The brand reputation score uses weighted sentiment aggregation where Positive reviews contribute +1, "
        "Neutral reviews contribute +0.5, and Negative reviews contribute -1. The normalized score is then "
        "converted into a percentage-style reputation indicator for dashboard reporting."
    )

    pdf.new_page()

    pdf.heading1("Chapter 5 - Implementation Methodology")
    pdf.divider()
    pdf.heading2("5.1 Technology Stack")
    pdf.bullet_list(
        [
            "Frontend: HTML, CSS, and JavaScript dashboard interface.",
            "Backend: Python Flask with REST-style API routes.",
            "ML and Analytics: pandas, NumPy, scikit-learn, joblib, matplotlib, seaborn.",
            "Persistence: CSV artifact storage with optional MongoDB integration.",
            "Realtime Connector Support: built-in mock connector, dataset CSV connector, and Kafka connector support.",
        ]
    )
    pdf.heading2("5.2 Workflow")
    pdf.numbered_list(
        [
            "Raw review CSV files are discovered from supported dataset folders.",
            "Review text is normalized, cleaned, and transformed into a processed review dataset.",
            "TF-IDF features are generated from cleaned reviews.",
            "Multiple Logistic Regression candidates are evaluated and the best one is calibrated.",
            "Predictions are produced for dataset-wide, batch, or single-review input.",
            "Brand reputation scores, trends, and dashboard analytics are generated from the outputs.",
            "Realtime reviews can be ingested and merged into the monitoring workflow.",
        ]
    )
    pdf.heading2("5.3 Model Training Strategy")
    pdf.paragraph(
        "The training pipeline uses a TF-IDF vectorizer with unigram and bigram features, up to 50,000 "
        "features, min_df filtering, max_df filtering, and sublinear term frequency scaling. Candidate "
        "Logistic Regression models are evaluated on validation performance, and the selected model is wrapped "
        "in a CalibratedClassifierCV sigmoid calibration layer to improve probability quality."
    )
    pdf.heading2("5.4 Prediction Logic")
    pdf.paragraph(
        "The prediction pipeline includes raw class probabilities, neutral-guard decision logic, confidence "
        "calibration, and multilingual sentiment guards. Final output includes the predicted sentiment, "
        "confidence, probability details, and rating mismatch indicators when a star rating is provided."
    )
    pdf.heading2("5.5 Realtime Review Flow")
    pdf.paragraph(
        "Realtime reviews are accepted either directly through the API or from polling connectors. Each "
        "realtime review is normalized, scored immediately, deduplicated by review ID, and stored in realtime "
        "review storage so that dashboard analytics can include live feedback in addition to baseline "
        "predictions."
    )

    pdf.new_page()

    pdf.heading1("Chapter 6 - Testing and Validation")
    pdf.divider()
    pdf.heading2("6.1 Testing Strategy")
    pdf.paragraph(
        "The project includes unit and route-level testing for preprocessing, multilingual normalization, "
        "prediction guards, brand scoring, connectors, dashboard payloads, and authentication behaviors. The "
        "tests help ensure that both model-related logic and backend application flows remain stable."
    )
    pdf.heading2("6.2 Current Verified Test Status")
    pdf.paragraph(
        "The latest local verification run executed 50 automated tests using the built-in Python unittest "
        "suite, and all 50 tests passed successfully."
    )
    pdf.heading2("6.3 Model Performance Snapshot")
    pdf.bullet_list(
        [
            "Selected Model: LogReg C=1.0 with sigmoid calibration.",
            "Validation Accuracy: 0.8672.",
            "Test Accuracy: 0.8688.",
            "Test Macro F1: 0.6153.",
            "Test Log Loss: 0.3824.",
        ]
    )
    pdf.heading2("6.4 Validation Observations")
    pdf.bullet_list(
        [
            "Positive and Negative classes perform strongly in the current artifact snapshot.",
            "Neutral-class performance is weaker, indicating an opportunity for future dataset balancing or refinement.",
            "Confidence calibration and language-specific evaluation utilities are included for model quality analysis.",
            "Route-level tests verify authentication, dashboard refresh behavior, and access control logic.",
        ]
    )

    pdf.new_page()

    pdf.heading1("Chapter 7 - Results, Advantages, and Limitations")
    pdf.divider()
    pdf.heading2("7.1 Current System Output Snapshot")
    pdf.paragraph(
        "The current generated brand score artifact reports a consolidated total of 714,505 scored reviews "
        "after merge and deduplication, with 53.90 percent positive, 7.71 percent neutral, and 38.40 percent "
        "negative sentiment. The current overall brand reputation score snapshot is 19.35, and the realtime "
        "review storage currently contributes 570 records to the monitoring layer."
    )
    pdf.heading2("7.2 Advantages")
    pdf.bullet_list(
        [
            "Provides a complete pipeline from raw review data to dashboard insights.",
            "Supports multilingual normalization and confidence-aware prediction.",
            "Combines offline batch analytics and realtime monitoring in one application.",
            "Includes role-based access and practical API endpoints for demo or academic use.",
            "Offers per-brand and platform-level reputation tracking rather than only per-review sentiment.",
        ]
    )
    pdf.heading2("7.3 Limitations")
    pdf.bullet_list(
        [
            "The Neutral class is harder to model accurately in the current dataset snapshot.",
            "The multilingual handling is lexicon- and rule-assisted rather than full neural translation.",
            "The frontend and backend entry files are currently large, which may affect long-term maintainability.",
            "The project is closer to an advanced academic prototype than a hardened production deployment.",
        ]
    )
    pdf.heading2("7.4 Discussion")
    pdf.paragraph(
        "The results show that the system is effective as an end-to-end review monitoring prototype, especially "
        "for positive and negative sentiment separation, dashboard reporting, and practical workflow "
        "integration. The main area for future improvement lies in finer-grained sentiment interpretation, "
        "especially for neutral and aspect-mixed review text."
    )

    pdf.new_page()

    pdf.heading1("Chapter 8 - Conclusion and Future Scope")
    pdf.divider()
    pdf.heading2("8.1 Conclusion")
    pdf.paragraph(
        "The AI-Based Online Review Analysis and Brand Reputation Monitoring System successfully demonstrates "
        "how an end-to-end AI-driven review analytics workflow can be built using practical web and machine "
        "learning tools. By combining preprocessing, multilingual normalization, model training, prediction, "
        "reputation scoring, dashboard visualization, and realtime ingestion, the project converts "
        "unstructured customer feedback into structured business insight."
    )
    pdf.paragraph(
        "The system is therefore both academically meaningful and practically relevant for organizations that "
        "need to monitor customer opinion, compare brands, and identify shifts in reputation over time."
    )
    pdf.heading2("8.2 Future Scope")
    pdf.bullet_list(
        [
            "Aspect-based sentiment analysis for delivery, price, quality, and customer support categories.",
            "Transformer-based or LLM-assisted review understanding for richer contextual interpretation.",
            "CI/CD, deployment automation, and stronger dependency pinning for reproducibility.",
            "Frontend modularization and additional dashboard drill-down views.",
            "Expanded connector ecosystem for more live review sources.",
        ]
    )

    pdf.new_page()

    pdf.heading1("References")
    pdf.numbered_list(
        [
            "Tom M. Mitchell, Machine Learning, McGraw-Hill, 1997.",
            "Christopher D. Manning, Prabhakar Raghavan, and Hinrich Schutze, Introduction to Information Retrieval, Cambridge University Press, 2008.",
            "Scikit-learn documentation for text vectorization, Logistic Regression, and probability calibration.",
            "Flask documentation for web application and session-based backend development.",
            "Research papers and technical references on sentiment analysis, review mining, and brand reputation analytics.",
        ]
    )
    pdf.heading2("Author Note")
    pdf.paragraph(
        "This report was prepared in an academic documentation style based on the reference format supplied by "
        "the user. Student identity, institution details, and guide information can be filled into the "
        "editable source before final submission if needed."
    )


def main() -> None:
    pdf = SimplePdf()
    build_report(pdf)
    out_dir = Path(__file__).resolve().parents[2] / "generated" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "brandpulse_project_report.pdf"
    out_path.write_bytes(pdf.finish())
    print(out_path)


if __name__ == "__main__":
    main()
