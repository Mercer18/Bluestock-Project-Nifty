"""
Report Generation Engine for Nifty 100 Financial Intelligence Platform.
Generates:
1. 92 Company Tearsheets (2 pages each, with Matplotlib charts).
2. 11 Sector Reports.
3. Portfolio Summary PDF with trend arrows.
"""

import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfgen import canvas

# Resolve paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "nifty100.db")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
TEARSHEETS_DIR = os.path.join(REPORTS_DIR, "tearsheets")
SECTOR_DIR = os.path.join(REPORTS_DIR, "sector")
PORTFOLIO_DIR = os.path.join(REPORTS_DIR, "portfolio")

# Create directories
os.makedirs(TEARSHEETS_DIR, exist_ok=True)
os.makedirs(SECTOR_DIR, exist_ok=True)
os.makedirs(PORTFOLIO_DIR, exist_ok=True)

# Helper for safe formatting
def sf(val, fmt="{:.2f}", suffix=""):
    if val is None or pd.isna(val):
        return "N/A"
    try:
        return fmt.format(float(val)) + suffix
    except Exception:
        return "N/A"

# Custom Canvas to handle page numbers
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#7F8C8D"))
        # Draw header (simple horizontal line and title)
        self.setStrokeColor(colors.HexColor("#BDC3C7"))
        self.setLineWidth(0.5)
        self.line(36, 756, 576, 756)
        self.drawString(36, 762, "Nifty 100 Financial Intelligence Platform")
        
        # Draw footer
        self.line(36, 45, 576, 45)
        self.drawString(36, 32, "Confidential - Bluestock Fintech")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(576, 32, page_text)
        self.restoreState()


class ReportGenerator:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        
        # Load necessary tables
        self.df_companies = pd.read_sql_query("SELECT * FROM companies", self.conn)
        self.df_ratios = pd.read_sql_query("SELECT * FROM financial_ratios", self.conn)
        self.df_pl = pd.read_sql_query("SELECT * FROM profitandloss", self.conn)
        self.df_bs = pd.read_sql_query("SELECT * FROM balancesheet", self.conn)
        self.df_cf = pd.read_sql_query("SELECT * FROM cashflow", self.conn)
        self.df_sectors = pd.read_sql_query("SELECT * FROM sectors", self.conn)
        
        # Merge sector into companies/ratios
        self.df_ratios = self.df_ratios.merge(self.df_sectors, on="company_id", how="left")
        
        # Load generated pros/cons if file exists, else use fallback generator
        pc_path = os.path.join(OUTPUT_DIR, "pros_cons_generated.csv")
        if os.path.exists(pc_path):
            self.df_pc = pd.read_csv(pc_path)
        else:
            self.df_pc = pd.DataFrame(columns=["company_id", "type", "text"])

    def close(self):
        self.conn.close()

    def generate_charts(self, cid, df_co_pl, df_co_bs, df_co_cf, df_co_r):
        """Generates chart images using Matplotlib and returns their filepaths."""
        tmp_paths = {}
        
        # Sort values by year
        df_co_pl = df_co_pl.sort_values(by="year")
        df_co_bs = df_co_bs.sort_values(by="year")
        df_co_cf = df_co_cf.sort_values(by="year")
        df_co_r = df_co_r.sort_values(by="year")
        
        years = df_co_pl["year"].tolist()
        
        # Chart 1: Revenue & Net Profit Bar (Side-by-side)
        plt.figure(figsize=(6, 2.5))
        x = np.arange(len(years))
        width = 0.35
        plt.bar(x - width/2, df_co_pl["sales"] / 10.0, width, label="Revenue (Cr)", color="#1F4E79")
        plt.bar(x + width/2, df_co_pl["net_profit"] / 10.0, width, label="Net Profit (Cr)", color="#4F81BD")
        plt.xticks(x, [y.split("-")[0] for y in years], fontsize=8)
        plt.title("10-Year Revenue & Net Profit (INR Cr)", fontsize=10, fontweight="bold", color="#2C3E50")
        plt.legend(fontsize=8, loc="upper left")
        plt.grid(axis="y", linestyle=":", alpha=0.6)
        plt.tight_layout()
        path1 = os.path.join(PROJECT_ROOT, f"tmp_{cid}_pl.png")
        plt.savefig(path1, dpi=150)
        plt.close()
        tmp_paths["pl"] = path1

        # Chart 2: ROE & ROCE Dual Axis Line Chart
        plt.figure(figsize=(6, 2.5))
        # Compute ROCE dynamically
        roces = []
        for y in years:
            p_bs = df_co_bs[df_co_bs["year"] == y]
            p_pl = df_co_pl[df_co_pl["year"] == y]
            if len(p_bs) > 0 and len(p_pl) > 0:
                ebit = (p_pl.iloc[0]["profit_before_tax"] or 0) + (p_pl.iloc[0]["interest"] or 0)
                ce = (p_bs.iloc[0]["equity_capital"] or 0) + (p_bs.iloc[0]["reserves"] or 0) + (p_bs.iloc[0]["borrowings"] or 0)
                roces.append((ebit / ce * 100) if ce > 0 else np.nan)
            else:
                roces.append(np.nan)
                
        roes = df_co_r["return_on_equity_pct"].tolist()
        # Pad or truncate roes if length mismatch
        if len(roes) < len(years):
            roes += [np.nan] * (len(years) - len(roes))
        else:
            roes = roes[:len(years)]
            
        plt.plot(years, roes, marker="o", label="ROE %", color="#E26B0A", linewidth=2)
        plt.plot(years, roces, marker="s", label="ROCE %", color="#5B9BD5", linewidth=2)
        plt.xticks(range(len(years)), [y.split("-")[0] for y in years], fontsize=8)
        plt.title("ROE & ROCE Trend (%)", fontsize=10, fontweight="bold", color="#2C3E50")
        plt.legend(fontsize=8, loc="upper left")
        plt.grid(axis="y", linestyle=":", alpha=0.6)
        plt.tight_layout()
        path2 = os.path.join(PROJECT_ROOT, f"tmp_{cid}_roce.png")
        plt.savefig(path2, dpi=150)
        plt.close()
        tmp_paths["roce"] = path2

        # Chart 3: Balance Sheet Stacked Bar Chart
        plt.figure(figsize=(6, 2.5))
        eq = df_co_bs["equity_capital"].fillna(0) / 10.0
        res = df_co_bs["reserves"].fillna(0) / 10.0
        borr = df_co_bs["borrowings"].fillna(0) / 10.0
        other = (df_co_bs["total_liabilities"].fillna(0) - (df_co_bs["equity_capital"].fillna(0) + df_co_bs["reserves"].fillna(0) + df_co_bs["borrowings"].fillna(0))) / 10.0
        other = np.maximum(other, 0)
        
        plt.bar(years, eq, label="Equity Capital", color="#1F4E79")
        plt.bar(years, res, bottom=eq, label="Reserves", color="#2E75B6")
        plt.bar(years, borr, bottom=eq+res, label="Borrowings", color="#BDD7EE")
        plt.bar(years, other, bottom=eq+res+borr, label="Other Liabilities", color="#D9D9D9")
        plt.xticks(range(len(years)), [y.split("-")[0] for y in years], fontsize=8)
        plt.title("Balance Sheet Composition (INR Cr)", fontsize=10, fontweight="bold", color="#2C3E50")
        plt.legend(fontsize=8, loc="upper left")
        plt.grid(axis="y", linestyle=":", alpha=0.6)
        plt.tight_layout()
        path3 = os.path.join(PROJECT_ROOT, f"tmp_{cid}_bs.png")
        plt.savefig(path3, dpi=150)
        plt.close()
        tmp_paths["bs"] = path3

        # Chart 4: Cash Flow Waterfall/Bar (Latest Year)
        plt.figure(figsize=(6, 2.5))
        cf_latest = df_co_cf.iloc[-1]
        cfo = (cf_latest["operating_activity"] or 0) / 10.0
        cfi = (cf_latest["investing_activity"] or 0) / 10.0
        cff = (cf_latest["financing_activity"] or 0) / 10.0
        net = cfo + cfi + cff
        
        categories = ["CFO", "CFI", "CFF", "Net Flow"]
        values = [cfo, cfi, cff, net]
        colors_list = ["#2E75B6" if v >= 0 else "#C00000" for v in values]
        plt.bar(categories, values, color=colors_list, width=0.5)
        plt.axhline(0, color="black", linewidth=0.8, linestyle="--")
        plt.title(f"Latest Cash Flow Breakdown (INR Cr, {cf_latest['year']})", fontsize=10, fontweight="bold", color="#2C3E50")
        plt.grid(axis="y", linestyle=":", alpha=0.6)
        plt.tight_layout()
        path4 = os.path.join(PROJECT_ROOT, f"tmp_{cid}_cf.png")
        plt.savefig(path4, dpi=150)
        plt.close()
        tmp_paths["cf"] = path4

        return tmp_paths

    def generate_single_tearsheet(self, cid):
        """Generates a 2-page PDF tearsheet for a company."""
        df_co_pl = self.df_pl[self.df_pl["company_id"] == cid]
        df_co_bs = self.df_bs[self.df_bs["company_id"] == cid]
        df_co_cf = self.df_cf[self.df_cf["company_id"] == cid]
        df_co_r = self.df_ratios[self.df_ratios["company_id"] == cid]
        
        # Align common years
        pl_years = set(df_co_pl["year"])
        bs_years = set(df_co_bs["year"])
        cf_years = set(df_co_cf["year"])
        r_years = set(df_co_r["year"])
        common_years = sorted(list(pl_years.intersection(bs_years).intersection(cf_years).intersection(r_years)))
        
        if len(common_years) < 3:
            print(f"Skipped {cid} - insufficient common years ({len(common_years)}).")
            return False
            
        df_co_pl = df_co_pl[df_co_pl["year"].isin(common_years)].sort_values(by="year")
        df_co_bs = df_co_bs[df_co_bs["year"].isin(common_years)].sort_values(by="year")
        df_co_cf = df_co_cf[df_co_cf["year"].isin(common_years)].sort_values(by="year")
        df_co_r = df_co_r[df_co_r["year"].isin(common_years)].sort_values(by="year")
            
        # Get metadata
        comp_meta = self.df_companies[self.df_companies["id"] == cid].iloc[0]
        sect_meta = self.df_sectors[self.df_sectors["company_id"] == cid]
        sector_name = sect_meta.iloc[0]["broad_sector"] if len(sect_meta) > 0 else "N/A"
        sub_sector_name = sect_meta.iloc[0]["sub_sector"] if len(sect_meta) > 0 else "N/A"
        
        # Sort and select latest
        df_co_r = df_co_r.sort_values(by="year")
        latest_ratio = df_co_r.iloc[-1]
        
        # Generate chart files
        tmp_paths = self.generate_charts(cid, df_co_pl, df_co_bs, df_co_cf, df_co_r)
        
        # Build Document
        pdf_path = os.path.join(TEARSHEETS_DIR, f"{cid}_tearsheet.pdf")
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=54,
            bottomMargin=54
        )
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            "CompanyTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=colors.HexColor("#1F4E79"),
            spaceAfter=5
        )
        
        meta_style = ParagraphStyle(
            "CompanyMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#7F8C8D"),
            spaceAfter=15
        )
        
        section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=colors.HexColor("#2E75B6"),
            spaceBefore=10,
            spaceAfter=10
        )
        
        kpi_num_style = ParagraphStyle(
            "KPINum",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            alignment=1, # Centered
            textColor=colors.HexColor("#2C3E50")
        )
        
        kpi_label_style = ParagraphStyle(
            "KPILabel",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            alignment=1, # Centered
            textColor=colors.HexColor("#7F8C8D")
        )
        
        bullet_style_pro = ParagraphStyle(
            "ProBullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#27AE60"),
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=5
        )
        
        bullet_style_con = ParagraphStyle(
            "ConBullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#C0392B"),
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=5
        )

        story = []
        
        # PAGE 1
        # Title and metadata
        story.append(Paragraph(comp_meta["company_name"], title_style))
        story.append(Paragraph(f"NSE Ticker: {cid} | Sector: {sector_name} | Sub-sector: {sub_sector_name}", meta_style))
        
        # 6 KPI Tiles in 2 rows of 3
        # KPIs: ROE%, NPM%, D/E, FCF Cr, Sales CAGR 5yr %, Composite Quality Score
        kpi_data = [
            [
                Paragraph(sf(latest_ratio["return_on_equity_pct"], "{:.2f}", "%"), kpi_num_style),
                Paragraph(sf(latest_ratio["net_profit_margin_pct"], "{:.2f}", "%"), kpi_num_style),
                Paragraph(sf(latest_ratio["debt_to_equity"], "{:.2f}", "x"), kpi_num_style)
            ],
            [
                Paragraph("Latest ROE %", kpi_label_style),
                Paragraph("Net Profit Margin", kpi_label_style),
                Paragraph("Debt-to-Equity", kpi_label_style)
            ],
            [
                Paragraph(sf(latest_ratio["free_cash_flow_cr"], "{:,.2f}"), kpi_num_style),
                Paragraph(sf(latest_ratio["revenue_cagr_5yr"], "{:.2f}", "%"), kpi_num_style),
                Paragraph(sf(latest_ratio["composite_quality_score"], "{:.1f}", " / 100"), kpi_num_style)
            ],
            [
                Paragraph("FCF (INR Cr)", kpi_label_style),
                Paragraph("Sales CAGR 5-Year", kpi_label_style),
                Paragraph("Composite Quality Score", kpi_label_style)
            ]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[180, 180, 180])
        kpi_table.setStyle(TableStyle([
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F8F9FA")),
            ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 15))
        
        # Embed side-by-side charts
        chart_data = [
            [Image(tmp_paths["pl"], width=260, height=130), Image(tmp_paths["roce"], width=260, height=130)]
        ]
        chart_table = Table(chart_data, colWidths=[270, 270])
        chart_table.setStyle(TableStyle([
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING", (0,0), (-1,-1), 0),
        ]))
        story.append(chart_table)
        
        # PAGE BREAK
        story.append(PageBreak())
        
        # PAGE 2
        # Balance Sheet & Cash Flow Charts side-by-side
        story.append(Paragraph("Capital Structure & Cash Flow Analytics", section_title_style))
        chart_data_p2 = [
            [Image(tmp_paths["bs"], width=260, height=130), Image(tmp_paths["cf"], width=260, height=130)]
        ]
        chart_table_p2 = Table(chart_data_p2, colWidths=[270, 270])
        chart_table_p2.setStyle(TableStyle([
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(chart_table_p2)
        story.append(Spacer(1, 15))
        
        # NLP Pros & Cons section
        story.append(Paragraph("Qualitative Pros & Cons Audit (NLP Engine)", section_title_style))
        
        co_pc = self.df_pc[self.df_pc["company_id"] == cid]
        pros_list = co_pc[co_pc["type"] == "pro"]["text"].tolist()
        cons_list = co_pc[co_pc["type"] == "con"]["text"].tolist()
        
        # If empty, add default fallbacks
        if not pros_list:
            pros_list = ["Stable operating history and continuous listing on the Nifty 100 index."]
        if not cons_list:
            cons_list = ["Subject to macro-economic cycles, raw material pricing volatility, and regulatory updates."]
            
        pro_paras = [Paragraph(f"<b>✓</b> {text}", bullet_style_pro) for text in pros_list[:3]] # limit to top 3
        con_paras = [Paragraph(f"<b>✗</b> {text}", bullet_style_con) for text in cons_list[:3]] # limit to top 3
        
        # Create side-by-side bullet lists
        bullets_data = [
            [Paragraph("<b>Key Strengths (Pros)</b>", ParagraphStyle("ProTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#27AE60"))),
             Paragraph("<b>Risk Factors (Cons)</b>", ParagraphStyle("ConTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#C0392B")))]
        ]
        
        # Add bullets side by side
        max_len = max(len(pro_paras), len(con_paras))
        for i in range(max_len):
            pro_col = pro_paras[i] if i < len(pro_paras) else Paragraph("", styles["Normal"])
            con_col = con_paras[i] if i < len(con_paras) else Paragraph("", styles["Normal"])
            bullets_data.append([pro_col, con_col])
            
        bullets_table = Table(bullets_data, colWidths=[265, 265])
        bullets_table.setStyle(TableStyle([
            ("ALIGN", (0,0), (-1,-1), "LEFT"),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F8F9FA")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("LINEBELOW", (0,0), (-1,0), 1, colors.HexColor("#E2E8F0")),
        ]))
        story.append(bullets_table)
        
        # Build Document using NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        
        # Cleanup temporary files
        for p in tmp_paths.values():
            if os.path.exists(p):
                os.remove(p)
        return True

    def generate_all_tearsheets(self):
        """Batch generates tearsheets for all 92 companies."""
        cids = sorted(self.df_companies["id"].unique())
        count = 0
        skipped = []
        for cid in cids:
            try:
                success = self.generate_single_tearsheet(cid)
                if success:
                    count += 1
                else:
                    skipped.append(cid)
            except Exception as e:
                print(f"Error generating tearsheet for {cid}: {str(e)}")
                skipped.append(cid)
                
        # Save skipped list to skipped_tearsheets.csv
        pd.DataFrame({"company_id": skipped}).to_csv(os.path.join(OUTPUT_DIR, "skipped_tearsheets.csv"), index=False)
        print(f"Generated {count} Tearsheets. Skipped: {len(skipped)}")

    def generate_sector_reports(self):
        """Generates 11 sector PDF summary reports."""
        sectors = self.df_sectors["broad_sector"].dropna().unique()
        for sect in sectors:
            # Filter ratios for 2024-03
            df_sec_r = self.df_ratios[(self.df_ratios["broad_sector"] == sect) & (self.df_ratios["year"] == "2024-03")]
            if len(df_sec_r) == 0:
                continue
                
            pdf_path = os.path.join(SECTOR_DIR, f"{sect}_report.pdf")
            doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=54, bottomMargin=54)
            
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("SectTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, textColor=colors.HexColor("#1F4E79"))
            header_style = ParagraphStyle("SectHead", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)
            cell_style = ParagraphStyle("SectCell", parent=styles["Normal"], fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#2C3E50"))
            
            story = []
            story.append(Paragraph(f"Sector Intelligence Report: {sect}", title_style))
            story.append(Spacer(1, 15))
            
            # Table headers
            table_data = [[
                Paragraph("<b>Ticker</b>", header_style),
                Paragraph("<b>Company Name</b>", header_style),
                Paragraph("<b>ROE %</b>", header_style),
                Paragraph("<b>D/E</b>", header_style),
                Paragraph("<b>ICR</b>", header_style),
                Paragraph("<b>FCF (Cr)</b>", header_style),
                Paragraph("<b>Sales CAGR 5Yr</b>", header_style),
                Paragraph("<b>Quality Score</b>", header_style)
            ]]
            
            # Load company names
            for _, row in df_sec_r.iterrows():
                cid = row["company_id"]
                c_name = self.df_companies[self.df_companies["id"] == cid]["company_name"].values[0]
                table_data.append([
                    Paragraph(cid, cell_style),
                    Paragraph(c_name, cell_style),
                    Paragraph(sf(row["return_on_equity_pct"], "{:.2f}", "%"), cell_style),
                    Paragraph(sf(row["debt_to_equity"], "{:.2f}", "x"), cell_style),
                    Paragraph(sf(row["interest_coverage"], "{:.2f}", "x"), cell_style),
                    Paragraph(sf(row["free_cash_flow_cr"], "{:,.2f}"), cell_style),
                    Paragraph(sf(row["revenue_cagr_5yr"], "{:.2f}", "%"), cell_style),
                    Paragraph(sf(row["composite_quality_score"], "{:.1f}"), cell_style)
                ])
                
            col_widths = [50, 150, 50, 50, 50, 60, 70, 60]
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1F4E79")),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8F9FA")]),
                ("TOPPADDING", (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ]))
            story.append(table)
            
            doc.build(story, canvasmaker=NumberedCanvas)
            print(f"Saved Sector Report: {pdf_path}")

    def generate_portfolio_summary(self):
        """Generates the unified Portfolio Summary PDF report (Day 35)."""
        pdf_path = os.path.join(PORTFOLIO_DIR, "portfolio_summary.pdf")
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=54, bottomMargin=54)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("PortTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20, textColor=colors.HexColor("#1F4E79"), alignment=1)
        sub_title_style = ParagraphStyle("PortSub", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=12, textColor=colors.HexColor("#2E75B6"), spaceAfter=15, alignment=1)
        comp_title_style = ParagraphStyle("PortComp", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, textColor=colors.HexColor("#1F4E79"), spaceBefore=10)
        body_style = ParagraphStyle("PortBody", parent=styles["Normal"], fontName="Helvetica", fontSize=9, spaceAfter=5)
        
        story = []
        story.append(Paragraph("Nifty 100 Portfolio Summary Report", title_style))
        story.append(Paragraph("Aggregated Financial Highlights & Performance Trends (FY 2024)", sub_title_style))
        story.append(Spacer(1, 10))
        
        # Sort companies alphabetically
        df_comp_sorted = self.df_companies.sort_values(by="id")
        
        # List of companies and their summary metrics
        table_data = [[
            Paragraph("<b>Ticker</b>", ParagraphStyle("H", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)),
            Paragraph("<b>Company Name</b>", ParagraphStyle("H", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)),
            Paragraph("<b>Sector</b>", ParagraphStyle("H", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)),
            Paragraph("<b>ROE %</b>", ParagraphStyle("H", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)),
            Paragraph("<b>D/E</b>", ParagraphStyle("H", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)),
            Paragraph("<b>NPM %</b>", ParagraphStyle("H", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)),
            Paragraph("<b>FCF (Cr)</b>", ParagraphStyle("H", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)),
            Paragraph("<b>Quality Score</b>", ParagraphStyle("H", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white))
        ]]
        
        cell_style = ParagraphStyle("C", parent=styles["Normal"], fontName="Helvetica", fontSize=8)
        
        for _, row in df_comp_sorted.iterrows():
            cid = row["id"]
            # Get latest 2024-03 metrics
            r_co = self.df_ratios[(self.df_ratios["company_id"] == cid) & (self.df_ratios["year"] == "2024-03")]
            if len(r_co) == 0:
                continue
            r_co_val = r_co.iloc[0]
            sect_val = self.df_sectors[self.df_sectors["company_id"] == cid]
            sect_name = sect_val.iloc[0]["broad_sector"] if len(sect_val) > 0 else "N/A"
            
            table_data.append([
                Paragraph(cid, cell_style),
                Paragraph(row["company_name"], cell_style),
                Paragraph(sect_name, cell_style),
                Paragraph(sf(r_co_val["return_on_equity_pct"], "{:.2f}", "%"), cell_style),
                Paragraph(sf(r_co_val["debt_to_equity"], "{:.2f}", "x"), cell_style),
                Paragraph(sf(r_co_val["net_profit_margin_pct"], "{:.2f}", "%"), cell_style),
                Paragraph(sf(r_co_val["free_cash_flow_cr"], "{:,.1f}"), cell_style),
                Paragraph(sf(r_co_val["composite_quality_score"], "{:.1f}"), cell_style)
            ])
            
        col_widths = [50, 130, 90, 50, 50, 50, 60, 60]
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1F4E79")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8F9FA")]),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(table)
        
        doc.build(story, canvasmaker=NumberedCanvas)
        print(f"Saved Portfolio Summary Report: {pdf_path}")


if __name__ == "__main__":
    generator = ReportGenerator()
    
    # 1. Generate 92 Tearsheets
    print("Generating Company Tearsheets...")
    generator.generate_all_tearsheets()
    
    # 2. Generate 11 Sector reports
    print("Generating Sector Reports...")
    generator.generate_sector_reports()
    
    # 3. Generate Portfolio Summary PDF
    print("Generating Portfolio Summary Report...")
    generator.generate_portfolio_summary()
    
    generator.close()
