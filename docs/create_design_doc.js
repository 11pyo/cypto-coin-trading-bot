const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageNumber, PageBreak,
  TableOfContents,
} = require("docx");

// ===== Shared Styles =====
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 60, bottom: 60, left: 100, right: 100 };
const headerShading = { fill: "1B3A5C", type: ShadingType.CLEAR };
const altShading = { fill: "F2F7FB", type: ShadingType.CLEAR };
const W = 9360; // US Letter content width (1" margins)

function hdr(text, width) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA }, shading: headerShading, margins: cellMargins,
    verticalAlign: "center",
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text, bold: true, color: "FFFFFF", font: "Arial", size: 20 })] })],
  });
}
function cell(text, width, opts = {}) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA }, margins: cellMargins,
    shading: opts.shading || undefined,
    children: [new Paragraph({ alignment: opts.align || AlignmentType.LEFT, children: [new TextRun({ text, font: "Arial", size: 20, bold: opts.bold || false })] })],
  });
}

function h1(text) { return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text, bold: true, font: "Arial", size: 36, color: "1B3A5C" })] }); }
function h2(text) { return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 160 }, children: [new TextRun({ text, bold: true, font: "Arial", size: 28, color: "2E75B6" })] }); }
function h3(text) { return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 120 }, children: [new TextRun({ text, bold: true, font: "Arial", size: 24, color: "404040" })] }); }
function p(text, opts = {}) { return new Paragraph({ spacing: { after: 120 }, indent: opts.indent ? { left: opts.indent } : undefined, children: [new TextRun({ text, font: "Arial", size: 20, bold: opts.bold || false, italics: opts.italic || false })] }); }
function pb() { return new Paragraph({ children: [new PageBreak()] }); }

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: "1B3A5C" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: "404040" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u00B7", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "sub-bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "-", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 360 } } } }] },
    ],
  },
  sections: [
    // ===== COVER PAGE =====
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } },
      },
      children: [
        new Paragraph({ spacing: { before: 3000 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: "ETH Auto-Trading Bot", font: "Arial", size: 56, bold: true, color: "1B3A5C" })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [new TextRun({ text: "Dual-Mode Strategy System", font: "Arial", size: 36, color: "2E75B6" })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 }, children: [new TextRun({ text: "Trend-Following + Mean-Reversion Adaptive Engine", font: "Arial", size: 24, color: "666666", italics: true })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, border: { top: { style: BorderStyle.SINGLE, size: 2, color: "2E75B6" } }, children: [] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: "System Design & Algorithm Specification", font: "Arial", size: 22, color: "333333" })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: "Version 2.0 - Dual-Mode Architecture", font: "Arial", size: 20, color: "666666" })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: "2026-03-26", font: "Arial", size: 20, color: "666666" })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: "Platform: Binance Spot (ETHUSDT)", font: "Arial", size: 20, color: "666666" })] }),

        new Paragraph({ spacing: { before: 800 } }),
        new Table({
          width: { size: 6000, type: WidthType.DXA }, columnWidths: [2400, 3600],
          rows: [
            new TableRow({ children: [hdr("Item", 2400), hdr("Detail", 3600)] }),
            new TableRow({ children: [cell("Trading Pair", 2400, { bold: true }), cell("ETH/USDT (Ethereum)", 3600)] }),
            new TableRow({ children: [cell("Exchange", 2400, { bold: true }), cell("Binance (via CCXT)", 3600, { shading: altShading })] }),
            new TableRow({ children: [cell("Strategy", 2400, { bold: true }), cell("Dual-Mode Adaptive", 3600)] }),
            new TableRow({ children: [cell("Language", 2400, { bold: true }), cell("Python 3.12+", 3600, { shading: altShading })] }),
            new TableRow({ children: [cell("Security", 2400, { bold: true }), cell("MOIS 2021 Compliant", 3600)] }),
          ],
        }),
      ],
    },
    // ===== TOC =====
    {
      properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "ETH Auto-Trading Bot - Design Specification", font: "Arial", size: 16, color: "999999", italics: true })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Page ", font: "Arial", size: 16 }), new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16 })] })] }) },
      children: [
        h1("Table of Contents"),
        new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
        pb(),

        // ===== 1. SYSTEM OVERVIEW =====
        h1("1. System Overview"),
        h2("1.1 Purpose"),
        p("This system is an automated cryptocurrency trading bot that trades ETH/USDT on Binance exchange. It employs a Dual-Mode strategy that dynamically switches between Trend-Following and Mean-Reversion modes based on real-time market conditions."),
        p("The bot continuously monitors 5 key market signals (EMA trend, volume, momentum, candle direction, MACD) and calculates a Trend Strength Score (0-100) every trading cycle. When the score exceeds the threshold (default: 50), the bot enters Trend-Following mode with larger positions and trailing stops. Otherwise, it operates in Mean-Reversion mode with standard oscillator-based buy/sell logic."),

        h2("1.2 Architecture"),
        new Table({
          width: { size: W, type: WidthType.DXA }, columnWidths: [2200, 7160],
          rows: [
            new TableRow({ children: [hdr("Module", 2200), hdr("Responsibility", 7160)] }),
            new TableRow({ children: [cell("main.py", 2200, { bold: true }), cell("Entry point, trading loop orchestration, dual-mode integration, graceful shutdown", 7160)] }),
            new TableRow({ children: [cell("strategy/composite.py", 2200, { bold: true }), cell("Dual-mode signal engine: TREND_UP / TREND_DOWN / RANGE mode evaluation, anti-bot filters", 7160, { shading: altShading })] }),
            new TableRow({ children: [cell("strategy/regime.py", 2200, { bold: true }), cell("Market regime detector with weighted scoring (EMA 30%, F&G 25%, Volume 15%, ATR 15%, Momentum 15%)", 7160)] }),
            new TableRow({ children: [cell("risk/manager.py", 2200, { bold: true }), cell("Multi-entry DCA position tracking, trailing stop, dynamic SL/TP, portfolio risk management", 7160, { shading: altShading })] }),
            new TableRow({ children: [cell("indicators/technical.py", 2200, { bold: true }), cell("RSI, MACD, Bollinger Bands, ATR, EMA, Volume Ratio, Momentum, Trend Strength Score", 7160)] }),
            new TableRow({ children: [cell("indicators/sentiment.py", 2200, { bold: true }), cell("Fear & Greed Index from alternative.me API (1-hour cache, 0-100 scale)", 7160, { shading: altShading })] }),
            new TableRow({ children: [cell("exchange/binance_client.py", 2200, { bold: true }), cell("CCXT-based Binance API wrapper, retry logic, rate limiting, order management", 7160)] }),
            new TableRow({ children: [cell("config/settings.py", 2200, { bold: true }), cell("Environment variable loader, credential validation, 45+ configurable parameters", 7160, { shading: altShading })] }),
          ],
        }),

        h2("1.3 Technology Stack"),
        new Table({
          width: { size: W, type: WidthType.DXA }, columnWidths: [2500, 3500, 3360],
          rows: [
            new TableRow({ children: [hdr("Component", 2500), hdr("Technology", 3500), hdr("Version", 3360)] }),
            new TableRow({ children: [cell("Language", 2500), cell("Python", 3500), cell("3.12+", 3360)] }),
            new TableRow({ children: [cell("Exchange API", 2500, { shading: altShading }), cell("CCXT (binance)", 3500, { shading: altShading }), cell("4.0+", 3360, { shading: altShading })] }),
            new TableRow({ children: [cell("Technical Analysis", 2500), cell("pandas-ta", 3500), cell("0.3.14b+", 3360)] }),
            new TableRow({ children: [cell("Data Processing", 2500, { shading: altShading }), cell("pandas", 3500, { shading: altShading }), cell("2.0+", 3360, { shading: altShading })] }),
            new TableRow({ children: [cell("Sentiment API", 2500), cell("alternative.me Fear & Greed", 3500), cell("REST API", 3360)] }),
            new TableRow({ children: [cell("Config Management", 2500, { shading: altShading }), cell("python-dotenv", 3500, { shading: altShading }), cell("1.0+", 3360, { shading: altShading })] }),
          ],
        }),
        pb(),

        // ===== 2. DUAL-MODE ALGORITHM =====
        h1("2. Dual-Mode Algorithm"),
        h2("2.1 Concept"),
        p("Traditional trading bots use a single strategy regardless of market conditions. This leads to a fundamental problem: mean-reversion strategies fail in trending markets (selling too early), while trend-following strategies fail in sideways markets (buying false breakouts)."),
        p("The Dual-Mode engine solves this by running TWO strategies and switching between them based on a real-time Trend Strength Score calculated from 5 independent market signals."),

        h2("2.2 Trend Strength Score (0-100)"),
        p("Every trading cycle, the system computes a composite score from these weighted signals:"),
        new Table({
          width: { size: W, type: WidthType.DXA }, columnWidths: [600, 2200, 1200, 5360],
          rows: [
            new TableRow({ children: [hdr("#", 600), hdr("Signal", 2200), hdr("Weight", 1200), hdr("Calculation", 5360)] }),
            new TableRow({ children: [cell("1", 600, { align: AlignmentType.CENTER }), cell("EMA Spread (20/50)", 2200, { bold: true }), cell("0-30 pts", 1200), cell("abs((EMA20 - EMA50) / EMA50) * 1000, capped at 30. Determines direction (UP if spread > 0.5%)", 5360)] }),
            new TableRow({ children: [cell("2", 600, { align: AlignmentType.CENTER, shading: altShading }), cell("Volume vs Average", 2200, { bold: true, shading: altShading }), cell("0-20 pts", 1200, { shading: altShading }), cell("Current volume / 20-period average. >1.5x = 20pts, >1.2x = 15pts, >1.0x = 10pts. Only counts if aligned with trend direction.", 5360, { shading: altShading })] }),
            new TableRow({ children: [cell("3", 600, { align: AlignmentType.CENTER }), cell("Price Momentum (5-bar)", 2200, { bold: true }), cell("0-25 pts", 1200), cell("abs(price_change_5bars) * 500, capped at 25. Aligned momentum adds; opposite momentum subtracts half.", 5360)] }),
            new TableRow({ children: [cell("4", 600, { align: AlignmentType.CENTER, shading: altShading }), cell("Consecutive Candles", 2200, { bold: true, shading: altShading }), cell("0-15 pts", 1200, { shading: altShading }), cell("Count of last 10 candles moving in trend direction. Each consecutive candle = 2 points.", 5360, { shading: altShading })] }),
            new TableRow({ children: [cell("5", 600, { align: AlignmentType.CENTER }), cell("MACD Histogram", 2200, { bold: true }), cell("0-10 pts", 1200), cell("abs(histogram / price) * 5000, capped at 10. Only counts if histogram sign matches trend direction.", 5360)] }),
          ],
        }),
        p(""),
        p("Mode Decision Rule:", { bold: true }),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Score >= 50 AND direction = UP  -->  TREND_UP mode", font: "Arial", size: 20, bold: true })] }),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Score >= 50 AND direction = DOWN  -->  TREND_DOWN mode", font: "Arial", size: 20, bold: true })] }),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Score < 50  -->  RANGE mode (mean-reversion)", font: "Arial", size: 20, bold: true })] }),

        h2("2.3 Mode: TREND_UP (Trend-Following)"),
        p("When a strong uptrend is confirmed, the bot rides the trend with maximum capital exposure and only exits via trailing stop."),
        new Table({
          width: { size: W, type: WidthType.DXA }, columnWidths: [2500, 6860],
          rows: [
            new TableRow({ children: [hdr("Parameter", 2500), hdr("TREND_UP Setting", 6860)] }),
            new TableRow({ children: [cell("Entry Condition", 2500, { bold: true }), cell("RSI < 45 (relaxed) OR price pulled back to EMA20 (+1%)", 6860)] }),
            new TableRow({ children: [cell("Position Size", 2500, { bold: true, shading: altShading }), cell("Base (15%) x 4.0 = 60% of available USDT", 6860, { shading: altShading })] }),
            new TableRow({ children: [cell("Sell Signal", 2500, { bold: true }), cell("DISABLED - RSI/BB sell signals are completely ignored", 6860)] }),
            new TableRow({ children: [cell("Exit Method", 2500, { bold: true, shading: altShading }), cell("Trailing Stop: 4% from peak price (only activates after price exceeds entry)", 6860, { shading: altShading })] }),
            new TableRow({ children: [cell("Hard Stop Loss", 2500, { bold: true }), cell("Entry price x (1 - 8% x 1.5) = 12% below entry", 6860)] }),
            new TableRow({ children: [cell("Min Holding", 2500, { bold: true, shading: altShading }), cell("6 bars (6 hours on 1h timeframe) before any exit allowed", 6860, { shading: altShading })] }),
            new TableRow({ children: [cell("Key Insight", 2500, { bold: true }), cell("In bull markets, RSI can stay above 70 for weeks. Selling on RSI > 70 causes massive opportunity loss. Trailing stop captures the trend until it actually reverses.", 6860)] }),
          ],
        }),

        h2("2.4 Mode: RANGE (Mean-Reversion)"),
        p("When no clear trend exists, the bot uses oscillator-based buy-low/sell-high logic."),
        new Table({
          width: { size: W, type: WidthType.DXA }, columnWidths: [2500, 6860],
          rows: [
            new TableRow({ children: [hdr("Parameter", 2500), hdr("RANGE Setting", 6860)] }),
            new TableRow({ children: [cell("BUY Condition", 2500, { bold: true }), cell("(RSI < 35 OR Price < BB_lower x 1.02) AND (Fear&Greed < 35 OR MACD histogram turning up)", 6860)] }),
            new TableRow({ children: [cell("SELL Condition", 2500, { bold: true, shading: altShading }), cell("(RSI > 72 OR Price > BB_upper x 0.98) AND (Fear&Greed > 75 OR MACD histogram turning down)", 6860, { shading: altShading })] }),
            new TableRow({ children: [cell("Position Size", 2500, { bold: true }), cell("Base: 15% of available USDT", 6860)] }),
            new TableRow({ children: [cell("Stop Loss", 2500, { bold: true, shading: altShading }), cell("8% below average entry price", 6860, { shading: altShading })] }),
            new TableRow({ children: [cell("Take Profit", 2500, { bold: true }), cell("10% above average entry price (fixed)", 6860)] }),
            new TableRow({ children: [cell("Min Holding", 2500, { bold: true, shading: altShading }), cell("3 bars (3 hours) before signal sell allowed", 6860, { shading: altShading })] }),
          ],
        }),

        h2("2.5 Mode: TREND_DOWN (Defensive)"),
        p("During confirmed downtrends, the bot minimizes exposure:"),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "NO new buy orders (only DCA on deep oversold RSI < 25)", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Position size: 50% of base (0.5x multiplier)", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Tight stop loss: 6% (base 8% x 0.75)", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Minimum holding: 2 bars only", font: "Arial", size: 20 })] }),
        pb(),

        // ===== 3. DCA =====
        h1("3. DCA (Dollar Cost Averaging)"),
        h2("3.1 Pyramid Entry Structure"),
        p("When an existing position drops below the average entry price by predefined thresholds, additional buy orders are placed with increasing size to lower the average cost basis:"),
        new Table({
          width: { size: W, type: WidthType.DXA }, columnWidths: [1500, 2000, 2000, 1900, 1960],
          rows: [
            new TableRow({ children: [hdr("Level", 1500), hdr("Drop Threshold", 2000), hdr("Size Multiplier", 2000), hdr("Example ($333)", 1900), hdr("Cumulative", 1960)] }),
            new TableRow({ children: [cell("L0 (Initial)", 1500, { bold: true }), cell("-", 2000, { align: AlignmentType.CENTER }), cell("1.0x", 2000, { align: AlignmentType.CENTER }), cell("$50", 1900, { align: AlignmentType.CENTER }), cell("$50", 1960, { align: AlignmentType.CENTER })] }),
            new TableRow({ children: [cell("L1 (DCA 1)", 1500, { bold: true, shading: altShading }), cell("-4% from avg", 2000, { align: AlignmentType.CENTER, shading: altShading }), cell("1.5x", 2000, { align: AlignmentType.CENTER, shading: altShading }), cell("$68", 1900, { align: AlignmentType.CENTER, shading: altShading }), cell("$118", 1960, { align: AlignmentType.CENTER, shading: altShading })] }),
            new TableRow({ children: [cell("L2 (DCA 2)", 1500, { bold: true }), cell("-8% from avg", 2000, { align: AlignmentType.CENTER }), cell("2.0x", 2000, { align: AlignmentType.CENTER }), cell("$84", 1900, { align: AlignmentType.CENTER }), cell("$202", 1960, { align: AlignmentType.CENTER })] }),
            new TableRow({ children: [cell("L3 (DCA 3)", 1500, { bold: true, shading: altShading }), cell("-12% from avg", 2000, { align: AlignmentType.CENTER, shading: altShading }), cell("2.5x", 2000, { align: AlignmentType.CENTER, shading: altShading }), cell("$97", 1900, { align: AlignmentType.CENTER, shading: altShading }), cell("$299", 1960, { align: AlignmentType.CENTER, shading: altShading })] }),
          ],
        }),

        h2("3.2 Safety Mechanisms"),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Total investment cap: 40% of total portfolio (prevents over-exposure)", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Signal confirmation required: BUY signal must re-trigger OR RSI < 25 (deep oversold)", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Anti-bot volume guard: DCA blocked if volume < 30% of average (avoids dead cat bounces)", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "SL/TP recalculated after each DCA entry based on new weighted average price", font: "Arial", size: 20 })] }),
        pb(),

        // ===== 4. ANTI-BOT =====
        h1("4. Anti-Bot Intelligence"),
        p("The system includes 4 countermeasures designed to avoid common algorithmic trading traps:"),
        new Table({
          width: { size: W, type: WidthType.DXA }, columnWidths: [2000, 3500, 3860],
          rows: [
            new TableRow({ children: [hdr("Defense", 2000), hdr("Mechanism", 3500), hdr("Purpose", 3860)] }),
            new TableRow({ children: [cell("Timing Jitter", 2000, { bold: true }), cell("1-30s random delay per cycle (secrets module)", 3500), cell("Avoid executing at same time as other bots (:00, :15, :30)", 3860)] }),
            new TableRow({ children: [cell("Volume Filter", 2000, { bold: true, shading: altShading }), cell("Reject signals when volume < 50% of 20-bar avg", 3500, { shading: altShading }), cell("Detect fakeout moves and bot-driven price manipulation", 3860, { shading: altShading })] }),
            new TableRow({ children: [cell("Momentum Filter", 2000, { bold: true }), cell("Block BUY if 5-bar momentum < -3%", 3500), cell("Avoid catching a falling knife during rapid decline", 3860)] }),
            new TableRow({ children: [cell("Trade Cooldown", 2000, { bold: true, shading: altShading }), cell("20-minute minimum between consecutive trades", 3500, { shading: altShading }), cell("Prevent rapid-fire entries that other bots exploit", 3860, { shading: altShading })] }),
          ],
        }),
        pb(),

        // ===== 5. RISK MANAGEMENT =====
        h1("5. Risk Management"),
        h2("5.1 Position Exit Priority"),
        p("Exit conditions are checked in strict priority order every cycle:"),
        new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun({ text: "Trailing Stop (TREND mode): If price drops 4% from peak (only after profit achieved)", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun({ text: "Hard Stop Loss: If price drops 8-12% below average entry (mode-dependent)", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun({ text: "Take Profit (RANGE mode only): If price rises 10% above average entry", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun({ text: "Signal Sell (RANGE mode only): RSI/BB overbought conditions + min holding met", font: "Arial", size: 20 })] }),

        h2("5.2 Mode-Dependent Risk Parameters"),
        new Table({
          width: { size: W, type: WidthType.DXA }, columnWidths: [2340, 2340, 2340, 2340],
          rows: [
            new TableRow({ children: [hdr("Parameter", 2340), hdr("TREND_UP", 2340), hdr("RANGE", 2340), hdr("TREND_DOWN", 2340)] }),
            new TableRow({ children: [cell("Position Size", 2340, { bold: true }), cell("60% (15% x 4)", 2340, { align: AlignmentType.CENTER }), cell("15%", 2340, { align: AlignmentType.CENTER }), cell("7.5% (15% x 0.5)", 2340, { align: AlignmentType.CENTER })] }),
            new TableRow({ children: [cell("Stop Loss", 2340, { bold: true, shading: altShading }), cell("12% (8% x 1.5)", 2340, { align: AlignmentType.CENTER, shading: altShading }), cell("8%", 2340, { align: AlignmentType.CENTER, shading: altShading }), cell("6% (8% x 0.75)", 2340, { align: AlignmentType.CENTER, shading: altShading })] }),
            new TableRow({ children: [cell("Take Profit", 2340, { bold: true }), cell("Trailing 4%", 2340, { align: AlignmentType.CENTER }), cell("Fixed 10%", 2340, { align: AlignmentType.CENTER }), cell("Fixed 8%", 2340, { align: AlignmentType.CENTER })] }),
            new TableRow({ children: [cell("Min Hold", 2340, { bold: true, shading: altShading }), cell("6 hours", 2340, { align: AlignmentType.CENTER, shading: altShading }), cell("3 hours", 2340, { align: AlignmentType.CENTER, shading: altShading }), cell("2 hours", 2340, { align: AlignmentType.CENTER, shading: altShading })] }),
            new TableRow({ children: [cell("Sell Signal", 2340, { bold: true }), cell("IGNORED", 2340, { align: AlignmentType.CENTER }), cell("Active", 2340, { align: AlignmentType.CENTER }), cell("Active", 2340, { align: AlignmentType.CENTER })] }),
          ],
        }),
        pb(),

        // ===== 6. TRADING CYCLE =====
        h1("6. Trading Cycle Flow"),
        p("Each cycle executes the following 8 steps (every 5 minutes + jitter):"),
        new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun({ text: "Apply Timing Jitter: Random 1-30 second delay (cryptographically secure)", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun({ text: "Fetch Market Data: 100 hourly OHLCV candles from Binance + current ticker price", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun({ text: "Calculate Indicators: RSI, MACD, BB, Volume Ratio, Momentum, ATR, EMA20, Trend Strength Score", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun({ text: "Fetch Sentiment: Fear & Greed Index from alternative.me (1-hour cache)", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun({ text: "Update Mode: Compare trend strength score to threshold (50), set TREND_UP/TREND_DOWN/RANGE", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun({ text: "Check Risk Exits: Trailing stop, hard SL, TP checked BEFORE strategy evaluation", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun({ text: "Evaluate Strategy: Mode-dependent signal generation (BUY/SELL/HOLD)", font: "Arial", size: 20 })] }),
        new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun({ text: "Execute & Log: Place orders on Binance, update position state, log dashboard", font: "Arial", size: 20 })] }),
        pb(),

        // ===== 7. SECURITY =====
        h1("7. Security Compliance"),
        p("All code follows MOIS Software Development Security Guide 2021 across 7 categories:"),
        new Table({
          width: { size: W, type: WidthType.DXA }, columnWidths: [3000, 6360],
          rows: [
            new TableRow({ children: [hdr("Category", 3000), hdr("Implementation", 6360)] }),
            new TableRow({ children: [cell("1. Input Validation", 3000, { bold: true }), cell("All numeric inputs validated for null/NaN/range. Volume ratio bounded. RSI/F&G range-checked.", 6360)] }),
            new TableRow({ children: [cell("2. Security Features", 3000, { bold: true, shading: altShading }), cell("API keys from env vars only. secrets module for randomness. No hard-coded credentials.", 6360, { shading: altShading })] }),
            new TableRow({ children: [cell("3. Time and State", 3000, { bold: true }), cell("Shutdown signal handler prevents infinite loop. Retry loops bounded at MAX_RETRIES=3.", 6360)] }),
            new TableRow({ children: [cell("4. Error Handling", 3000, { bold: true, shading: altShading }), cell("Generic messages to console. Full tracebacks to rotating log file only. No empty except blocks.", 6360, { shading: altShading })] }),
            new TableRow({ children: [cell("5. Code Errors", 3000, { bold: true }), cell("Null checks on all positions/indicators before access. Division by zero prevention on all ratios.", 6360)] }),
            new TableRow({ children: [cell("6. Encapsulation", 3000, { bold: true, shading: altShading }), cell("Internal arrays returned as copies. Position data accessed via properties.", 6360, { shading: altShading })] }),
            new TableRow({ children: [cell("7. API Misuse", 3000, { bold: true }), cell("CCXT handles rate limiting. Exponential backoff on network errors. SSL verification enabled.", 6360)] }),
          ],
        }),
        pb(),

        // ===== 8. CONFIGURATION =====
        h1("8. Configuration Reference"),
        p("All parameters are loaded from the .env file via environment variables:"),
        h3("8.1 Core Trading Parameters"),
        new Table({
          width: { size: W, type: WidthType.DXA }, columnWidths: [3800, 1560, 4000],
          rows: [
            new TableRow({ children: [hdr("Parameter", 3800), hdr("Default", 1560), hdr("Description", 4000)] }),
            new TableRow({ children: [cell("MAX_POSITION_PERCENT", 3800), cell("0.15", 1560, { align: AlignmentType.CENTER }), cell("Base position size (15% of USDT)", 4000)] }),
            new TableRow({ children: [cell("STOP_LOSS_PERCENT", 3800, { shading: altShading }), cell("0.08", 1560, { align: AlignmentType.CENTER, shading: altShading }), cell("Base stop loss distance (8%)", 4000, { shading: altShading })] }),
            new TableRow({ children: [cell("TAKE_PROFIT_PERCENT", 3800), cell("0.10", 1560, { align: AlignmentType.CENTER }), cell("Fixed take profit target (10%)", 4000)] }),
            new TableRow({ children: [cell("TREND_THRESHOLD", 3800, { shading: altShading }), cell("50.0", 1560, { align: AlignmentType.CENTER, shading: altShading }), cell("Score threshold for trend mode activation", 4000, { shading: altShading })] }),
            new TableRow({ children: [cell("TREND_POSITION_MULTIPLIER", 3800), cell("4.0", 1560, { align: AlignmentType.CENTER }), cell("Position size multiplier in trend mode", 4000)] }),
            new TableRow({ children: [cell("TREND_TRAILING_STOP_PCT", 3800, { shading: altShading }), cell("0.04", 1560, { align: AlignmentType.CENTER, shading: altShading }), cell("Trailing stop distance from peak (4%)", 4000, { shading: altShading })] }),
            new TableRow({ children: [cell("TREND_MIN_HOLD_BARS", 3800), cell("6", 1560, { align: AlignmentType.CENTER }), cell("Minimum bars before exit in trend mode", 4000)] }),
            new TableRow({ children: [cell("RANGE_MIN_HOLD_BARS", 3800, { shading: altShading }), cell("3", 1560, { align: AlignmentType.CENTER, shading: altShading }), cell("Minimum bars before exit in range mode", 4000, { shading: altShading })] }),
            new TableRow({ children: [cell("DRY_RUN", 3800), cell("true", 1560, { align: AlignmentType.CENTER }), cell("Sandbox mode (true) or live trading (false)", 4000)] }),
          ],
        }),
        pb(),

        // ===== 9. DISCLAIMER =====
        h1("9. Disclaimer"),
        p("This software is provided for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. Past simulation results do not guarantee future performance. The developers are not responsible for any financial losses incurred through the use of this software.", { italic: true }),
        p("Key risks include but are not limited to: exchange downtime, API rate limiting, slippage, flash crashes, regulatory changes, and network failures. Always start with DRY_RUN=true and test thoroughly before deploying with real funds.", { italic: true }),
      ],
    },
  ],
});

Packer.toBuffer(doc).then(buffer => {
  const outPath = "D:\\개발한 프로그램들\\cypto-coin-trading-bot\\docs\\ETH_Trading_Bot_Design_Specification.docx";
  fs.writeFileSync(outPath, buffer);
  console.log("Document created: " + outPath);
});
