/*!
 * brand-engine — Chart.js helper (v2)
 *
 * Reads the brand chart tokens from the page and keeps charts in sync with the
 * active theme. The page loads Chart.js itself (CDN, only on pages with a
 * chart); this file assumes `window.Chart` exists and degrades to `null`
 * when it does not.
 *
 * Tokens read:
 *   --b-chart-1 .. --b-chart-8   series colours (3:1 against --b-surface)
 *   --b-fg-subtle                axis and legend labels
 *   --b-line                     grid lines and borders
 *   --b-surface                  canvas background, point borders
 *
 * Usage:
 *   <canvas id="receita" height="240"></canvas>
 *   <script src="brand-charts.js"></script>
 *   <script>
 *     BrandCharts.create("receita", {
 *       type: "line",
 *       data: { labels: ["Jan", "Fev"], datasets: [{ label: "Receita", data: [10, 12] }] }
 *     });
 *   </script>
 *
 * Theme changes are observed on `document.documentElement[data-theme]`; every
 * registered chart is rebuilt with the new palette. The caller's config is
 * never mutated: only colours that were omitted are filled in.
 */
(function (window, document) {
  "use strict";

  var CHART_TOKENS = [
    "--b-chart-1",
    "--b-chart-2",
    "--b-chart-3",
    "--b-chart-4",
    "--b-chart-5",
    "--b-chart-6",
    "--b-chart-7",
    "--b-chart-8"
  ];

  var FALLBACK = {
    chart: [
      "#1F6F8B",
      "#B45309",
      "#2F7D4F",
      "#7C3AED",
      "#B91C1C",
      "#0E7490",
      "#854D0E",
      "#374151"
    ],
    fg: "#6B7280",
    line: "#D1D5DB",
    surface: "#FFFFFF"
  };

  function readToken(name, fallback) {
    var value = "";
    try {
      value = window.getComputedStyle(document.documentElement).getPropertyValue(name);
    } catch (error) {
      value = "";
    }
    value = (value || "").trim();
    return value || fallback;
  }

  function colors() {
    var chart = [];
    for (var index = 0; index < CHART_TOKENS.length; index += 1) {
      chart.push(readToken(CHART_TOKENS[index], FALLBACK.chart[index]));
    }
    return {
      chart: chart,
      fg: readToken("--b-fg-subtle", FALLBACK.fg),
      line: readToken("--b-line", FALLBACK.line),
      surface: readToken("--b-surface", FALLBACK.surface)
    };
  }

  function copy(value) {
    if (Array.isArray(value)) {
      return value.slice();
    }
    if (value && typeof value === "object") {
      var clone = {};
      var keys = Object.keys(value);
      for (var index = 0; index < keys.length; index += 1) {
        clone[keys[index]] = value[keys[index]];
      }
      return clone;
    }
    return value;
  }

  function isCircular(type) {
    return type === "doughnut" || type === "pie" || type === "polarArea";
  }

  function paintDataset(dataset, palette, index, type) {
    var painted = copy(dataset);
    var accent = palette.chart[index % palette.chart.length];
    if (isCircular(type)) {
      if (!painted.backgroundColor) {
        painted.backgroundColor = palette.chart.slice();
      }
      if (!painted.borderColor) {
        painted.borderColor = palette.surface;
      }
      return painted;
    }
    if (type === "line" || type === "radar") {
      if (!painted.borderColor) {
        painted.borderColor = accent;
      }
      if (!painted.backgroundColor) {
        painted.backgroundColor = accent;
      }
      if (!painted.pointBackgroundColor) {
        painted.pointBackgroundColor = accent;
      }
      if (painted.pointBorderColor === undefined) {
        painted.pointBorderColor = palette.surface;
      }
      return painted;
    }
    if (!painted.backgroundColor) {
      painted.backgroundColor = accent;
    }
    if (!painted.borderColor) {
      painted.borderColor = accent;
    }
    return painted;
  }

  function paintScale(scale, palette) {
    var painted = copy(scale) || {};
    painted.grid = copy(painted.grid) || {};
    if (painted.grid.color === undefined) {
      painted.grid.color = palette.line;
    }
    painted.ticks = copy(painted.ticks) || {};
    if (painted.ticks.color === undefined) {
      painted.ticks.color = palette.fg;
    }
    painted.border = copy(painted.border) || {};
    if (painted.border.color === undefined) {
      painted.border.color = palette.line;
    }
    return painted;
  }

  function paintOptions(options, palette, type) {
    var painted = copy(options) || {};
    painted.plugins = copy(painted.plugins) || {};

    painted.plugins.legend = copy(painted.plugins.legend) || {};
    painted.plugins.legend.labels = copy(painted.plugins.legend.labels) || {};
    if (painted.plugins.legend.labels.color === undefined) {
      painted.plugins.legend.labels.color = palette.fg;
    }

    painted.plugins.title = copy(painted.plugins.title) || {};
    if (painted.plugins.title.color === undefined) {
      painted.plugins.title.color = palette.fg;
    }

    if (isCircular(type)) {
      return painted;
    }

    painted.scales = copy(painted.scales) || {};
    var axes = type === "radar" ? ["r"] : ["x", "y"];
    for (var index = 0; index < axes.length; index += 1) {
      var axis = axes[index];
      painted.scales[axis] = paintScale(painted.scales[axis], palette);
    }
    return painted;
  }

  var registry = {};
  var instances = {};

  function constructor() {
    return typeof window.Chart === "function" ? window.Chart : null;
  }

  function build(canvasId, config, Constructor) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || !config || !config.type || !config.data) {
      return null;
    }

    if (instances[canvasId]) {
      instances[canvasId].destroy();
      instances[canvasId] = null;
    }

    var palette = colors();
    var source = config.data.datasets || [];
    var datasets = [];
    for (var index = 0; index < source.length; index += 1) {
      datasets.push(paintDataset(source[index], palette, index, config.type));
    }

    var painted = {
      type: config.type,
      data: copy(config.data),
      options: paintOptions(config.options, palette, config.type)
    };
    painted.data.datasets = datasets;

    var chart = new Constructor(canvas, painted);
    instances[canvasId] = chart;
    registry[canvasId] = config;
    return chart;
  }

  /**
   * Create (or recreate) the chart on `canvasId`.
   * Returns the Chart instance, or null when the canvas or Chart.js is absent.
   */
  function create(canvasId, config) {
    var Constructor = constructor();
    if (!Constructor) {
      return null;
    }
    return build(canvasId, config, Constructor);
  }

  /**
   * Rebuild every chart registered through create() with the current tokens.
   * Charts whose canvas left the DOM are dropped.
   */
  function refresh() {
    var Constructor = constructor();
    var ids = Object.keys(registry);
    for (var index = 0; index < ids.length; index += 1) {
      var canvasId = ids[index];
      if (!Constructor || !document.getElementById(canvasId)) {
        delete registry[canvasId];
        delete instances[canvasId];
        continue;
      }
      build(canvasId, registry[canvasId], Constructor);
    }
  }

  function watchTheme() {
    if (typeof window.MutationObserver !== "function" || !document.documentElement) {
      return;
    }
    var observer = new window.MutationObserver(function (records) {
      for (var index = 0; index < records.length; index += 1) {
        if (records[index].type === "attributes" && records[index].attributeName === "data-theme") {
          refresh();
          return;
        }
      }
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"]
    });
  }

  watchTheme();

  window.BrandCharts = {
    colors: colors,
    create: create,
    refresh: refresh
  };
})(window, document);
