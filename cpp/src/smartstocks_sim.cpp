#include <algorithm>
#include <cmath>
#include <fstream>
#include <future>
#include <iostream>
#include <limits>
#include <mutex>
#include <random>
#include <sstream>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace {
struct Config {
    std::size_t num_simulations = 1000;
    std::size_t sim_time = 30;
    std::size_t interval_minutes = 60;
    double initial_condition = 1.0;
    double drift = 0.0;
    double volatility = 0.1;
    double average_reduction = 0.0;
    double bull = 0.0;
    double bear = 0.0;
    double min_cap = 0.0;
    double max_cap = 0.0;
    std::size_t incremental_adjustment_steps = 1;
    double jump_mean = 0.0;
    double jump_std = 0.0;
    double jump_intensity = 0.0;
    std::size_t threads = 1;
    std::size_t window_size = 20;
    std::size_t macd_short_window = 12;
    std::size_t macd_long_window = 26;
    std::size_t macd_signal_window = 9;
    std::string simulation_mode = "standard";
    bool output_simulated_prices = false;
    long long seed = -1;
};

bool parse_line(const std::string &line, std::string &key, std::string &value) {
    auto trimmed = line;
    auto comment_pos = trimmed.find('#');
    if (comment_pos != std::string::npos) {
        trimmed = trimmed.substr(0, comment_pos);
    }
    auto first_non_space = trimmed.find_first_not_of(" \t\r\n");
    if (first_non_space == std::string::npos) {
        return false;
    }
    trimmed = trimmed.substr(first_non_space);
    auto last_non_space = trimmed.find_last_not_of(" \t\r\n");
    if (last_non_space != std::string::npos) {
        trimmed = trimmed.substr(0, last_non_space + 1);
    }

    auto pos = trimmed.find('=');
    if (pos == std::string::npos) {
        return false;
    }
    key = trimmed.substr(0, pos);
    value = trimmed.substr(pos + 1);

    auto key_end = key.find_last_not_of(" \t\r\n");
    if (key_end != std::string::npos) {
        key = key.substr(0, key_end + 1);
    }
    auto value_begin = value.find_first_not_of(" \t\r\n");
    if (value_begin != std::string::npos) {
        value = value.substr(value_begin);
    }
    auto value_end = value.find_last_not_of(" \t\r\n");
    if (value_end != std::string::npos) {
        value = value.substr(0, value_end + 1);
    }
    return !key.empty() && !value.empty();
}

Config load_config(const std::string &path) {
    Config config;
    std::ifstream input(path);
    if (!input.is_open()) {
        throw std::runtime_error("Unable to open config file: " + path);
    }

    std::string line;
    while (std::getline(input, line)) {
        std::string key;
        std::string value;
        if (!parse_line(line, key, value)) {
            continue;
        }

        auto to_double = [&]() {
            return std::stod(value);
        };
        auto to_size = [&]() {
            auto converted = static_cast<std::size_t>(std::stoll(value));
            return converted;
        };
        auto to_bool = [&]() {
            return value == "true" || value == "True" || value == "1";
        };
        if (key == "num_simulations") {
            config.num_simulations = to_size();
        } else if (key == "sim_time") {
            config.sim_time = to_size();
        } else if (key == "interval_minutes") {
            config.interval_minutes = to_size();
        } else if (key == "initial_condition") {
            config.initial_condition = to_double();
        } else if (key == "drift") {
            config.drift = to_double();
        } else if (key == "volatility") {
            config.volatility = to_double();
        } else if (key == "average_reduction") {
            config.average_reduction = to_double();
        } else if (key == "bull") {
            config.bull = to_double();
        } else if (key == "bear") {
            config.bear = to_double();
        } else if (key == "min_cap") {
            config.min_cap = to_double();
        } else if (key == "max_cap") {
            config.max_cap = to_double();
        } else if (key == "incremental_adjustment_steps") {
            config.incremental_adjustment_steps = std::max<std::size_t>(1, to_size());
        } else if (key == "jump_mean") {
            config.jump_mean = to_double();
        } else if (key == "jump_std") {
            config.jump_std = to_double();
        } else if (key == "jump_intensity") {
            config.jump_intensity = to_double();
        } else if (key == "threads") {
            config.threads = std::max<std::size_t>(1, to_size());
        } else if (key == "window_size") {
            config.window_size = std::max<std::size_t>(1, to_size());
        } else if (key == "macd_short_window") {
            config.macd_short_window = std::max<std::size_t>(1, to_size());
        } else if (key == "macd_long_window") {
            config.macd_long_window = std::max<std::size_t>(1, to_size());
        } else if (key == "macd_signal_window") {
            config.macd_signal_window = std::max<std::size_t>(1, to_size());
        } else if (key == "simulation_mode") {
            config.simulation_mode = value;
        } else if (key == "output_simulated_prices") {
            config.output_simulated_prices = to_bool();
        } else if (key == "seed") {
            config.seed = std::stoll(value);
        }
    }

    if (config.max_cap <= config.min_cap) {
        config.max_cap = std::max(config.max_cap, config.min_cap + 1.0);
    }

    if (config.threads == 0) {
        config.threads = 1;
    }

    return config;
}

std::vector<int> detect_head_and_shoulders(const std::vector<double> &prices, std::size_t window_size) {
    const std::size_t n = prices.size();
    std::vector<int> patterns(n, 0);
    if (window_size == 0 || n < 2 * window_size || window_size < 4) {
        return patterns;
    }

    const std::size_t half_window = window_size / 2;
    if (half_window == 0) {
        return patterns;
    }

    for (std::size_t i = window_size; i + window_size < n; ++i) {
        const std::size_t start = i - window_size;
        const std::size_t end = i + window_size;

        double left_max = -std::numeric_limits<double>::infinity();
        double head_max = -std::numeric_limits<double>::infinity();
        double right_max = -std::numeric_limits<double>::infinity();
        double head_min = std::numeric_limits<double>::infinity();

        for (std::size_t j = start; j < start + half_window; ++j) {
            left_max = std::max(left_max, prices[j]);
        }
        for (std::size_t j = start + half_window; j < start + window_size; ++j) {
            head_max = std::max(head_max, prices[j]);
            head_min = std::min(head_min, prices[j]);
        }
        for (std::size_t j = start + window_size; j < end; ++j) {
            right_max = std::max(right_max, prices[j]);
        }

        if (left_max < head_max && right_max < head_max && left_max > head_min && right_max > head_min) {
            patterns[i] = 1;
        }
    }

    return patterns;
}

struct MacdResult {
    std::vector<double> macd_line;
    std::vector<double> signal_line;
};

MacdResult compute_macd(const std::vector<double> &prices, std::size_t short_window, std::size_t long_window, std::size_t signal_window) {
    const std::size_t n = prices.size();
    MacdResult result;
    result.macd_line.resize(n, 0.0);
    result.signal_line.resize(n, 0.0);

    if (n == 0) {
        return result;
    }

    const double short_alpha = 2.0 / (static_cast<double>(short_window) + 1.0);
    const double long_alpha = 2.0 / (static_cast<double>(long_window) + 1.0);
    const double signal_alpha = 2.0 / (static_cast<double>(signal_window) + 1.0);

    double short_ema = prices[0];
    double long_ema = prices[0];
    double signal = short_ema - long_ema;

    result.macd_line[0] = signal;
    result.signal_line[0] = signal;

    for (std::size_t i = 1; i < n; ++i) {
        short_ema = short_alpha * prices[i] + (1.0 - short_alpha) * short_ema;
        long_ema = long_alpha * prices[i] + (1.0 - long_alpha) * long_ema;
        const double macd = short_ema - long_ema;
        signal = signal_alpha * macd + (1.0 - signal_alpha) * signal;
        result.macd_line[i] = macd;
        result.signal_line[i] = signal;
    }

    return result;
}

struct SimulationContext {
    const Config &config;
    std::size_t total_intervals;
    double dt;
    double bull_increment;
    double bear_increment;
    double average_reduction_increment;
};

void run_simulations(std::size_t start,
                     std::size_t end,
                     const SimulationContext &ctx,
                     std::vector<double> &results,
                     std::mutex &write_mutex) {
    (void)write_mutex;

    std::mt19937_64 rng;
    if (ctx.config.seed >= 0) {
        rng.seed(static_cast<std::mt19937_64::result_type>(ctx.config.seed) + start);
    } else {
        std::random_device rd;
        rng.seed(rd() + static_cast<unsigned>(start));
    }

    std::normal_distribution<double> gbm_dist(ctx.config.drift * ctx.dt,
                                              ctx.config.volatility * std::sqrt(ctx.dt));
    std::normal_distribution<double> jump_dist(ctx.config.jump_mean, ctx.config.jump_std);
    std::poisson_distribution<int> poisson_dist(ctx.config.jump_intensity * ctx.dt);

    const std::size_t intervals = ctx.total_intervals;
    std::vector<double> data(intervals + 1, ctx.config.initial_condition);

    for (std::size_t sim = start; sim < end; ++sim) {
        data[0] = ctx.config.initial_condition;
        for (std::size_t step = 0; step < intervals; ++step) {
            const double normal_shock = gbm_dist(rng);
            const int num_jumps = poisson_dist(rng);
            double jump_shock = 0.0;
            if (ctx.config.jump_std == 0.0) {
                jump_shock = static_cast<double>(num_jumps) * ctx.config.jump_mean;
            } else {
                for (int j = 0; j < num_jumps; ++j) {
                    jump_shock += jump_dist(rng);
                }
            }
            const double shock = normal_shock + jump_shock;
            double next_value = data[step] * std::exp(shock);
            next_value = std::min(std::max(next_value, ctx.config.min_cap), ctx.config.max_cap);
            data[step + 1] = next_value;
        }

        auto patterns = detect_head_and_shoulders(data, ctx.config.window_size);
        int pending_reduction_adjustments = 0;
        for (std::size_t i = 1; i < data.size(); ++i) {
            if (pending_reduction_adjustments > 0) {
                data[i] *= (1.0 - ctx.average_reduction_increment);
                --pending_reduction_adjustments;
            }
            if (patterns[i] == 1) {
                pending_reduction_adjustments = static_cast<int>(ctx.config.incremental_adjustment_steps);
            }
        }

        auto macd_result = compute_macd(data, ctx.config.macd_short_window, ctx.config.macd_long_window, ctx.config.macd_signal_window);
        int pending_bull_adjustments = 0;
        int pending_bear_adjustments = 0;
        for (std::size_t i = 1; i < data.size(); ++i) {
            if (pending_bull_adjustments > 0) {
                data[i] *= (1.0 + ctx.bull_increment);
                --pending_bull_adjustments;
            }
            if (pending_bear_adjustments > 0) {
                data[i] *= (1.0 - ctx.bear_increment);
                --pending_bear_adjustments;
            }
            if (macd_result.macd_line[i] > macd_result.signal_line[i] &&
                macd_result.macd_line[i - 1] <= macd_result.signal_line[i - 1]) {
                pending_bull_adjustments = static_cast<int>(ctx.config.incremental_adjustment_steps);
            } else if (macd_result.macd_line[i] < macd_result.signal_line[i] &&
                       macd_result.macd_line[i - 1] >= macd_result.signal_line[i - 1]) {
                pending_bear_adjustments = static_cast<int>(ctx.config.incremental_adjustment_steps);
            }
        }

        const std::size_t offset = sim * intervals;
        for (std::size_t i = 0; i < intervals; ++i) {
            results[offset + i] = data[i + 1];
        }
    }
}

void run_log_return_interval_simulations(std::size_t start,
                                         std::size_t end,
                                         const SimulationContext &ctx,
                                         std::vector<double> &results) {
    std::mt19937_64 rng;
    if (ctx.config.seed >= 0) {
        rng.seed(static_cast<std::mt19937_64::result_type>(ctx.config.seed) + start);
    } else {
        std::random_device rd;
        rng.seed(rd() + static_cast<unsigned>(start));
    }

    std::normal_distribution<double> log_return_dist(ctx.config.drift * ctx.dt,
                                                     ctx.config.volatility * std::sqrt(ctx.dt));

    const std::size_t intervals = ctx.total_intervals;
    for (std::size_t sim = start; sim < end; ++sim) {
        double price = ctx.config.initial_condition;
        const std::size_t offset = sim * intervals;
        for (std::size_t step = 0; step < intervals; ++step) {
            const double future_log_return = log_return_dist(rng);
            price *= std::exp(future_log_return);
            results[offset + step] = price;
        }
    }
}

double interpolate_percentile(const std::vector<double> &sorted_values, double percentile) {
    if (sorted_values.empty()) {
        return std::numeric_limits<double>::quiet_NaN();
    }

    const double scaled_index = percentile * static_cast<double>(sorted_values.size() - 1);
    const auto lower_index = static_cast<std::size_t>(std::floor(scaled_index));
    const auto upper_index = static_cast<std::size_t>(std::ceil(scaled_index));
    const double fraction = scaled_index - static_cast<double>(lower_index);

    const double lower_value = sorted_values[lower_index];
    const double upper_value = sorted_values[upper_index];

    if (upper_index == lower_index) {
        return lower_value;
    }

    return lower_value + fraction * (upper_value - lower_value);
}

void write_numeric(std::ofstream &output, double value) {
    if (std::isfinite(value)) {
        output << value;
    } else {
        output << "null";
    }
}

void write_flat_array(std::ofstream &output, const std::vector<double> &values) {
    output << "[";
    for (std::size_t i = 0; i < values.size(); ++i) {
        write_numeric(output, values[i]);
        if (i + 1 != values.size()) {
            output << ", ";
        }
    }
    output << "]";
}

void write_matrix(std::ofstream &output,
                  const std::vector<double> &values,
                  std::size_t rows,
                  std::size_t columns) {
    output << "[";
    for (std::size_t row = 0; row < rows; ++row) {
        output << "[";
        const std::size_t offset = row * columns;
        for (std::size_t column = 0; column < columns; ++column) {
            write_numeric(output, values[offset + column]);
            if (column + 1 != columns) {
                output << ", ";
            }
        }
        output << "]";
        if (row + 1 != rows) {
            output << ", ";
        }
    }
    output << "]";
}

void write_output(const std::string &path,
                  const std::vector<double> &means,
                  const std::vector<double> &stds,
                  const std::vector<double> &percentile_05,
                  const std::vector<double> &percentile_95,
                  const std::vector<double> *simulated_prices = nullptr,
                  std::size_t simulation_rows = 0,
                  std::size_t simulation_columns = 0) {
    std::ofstream output(path);
    if (!output.is_open()) {
        throw std::runtime_error("Unable to open output file: " + path);
    }

    output << "{\n";
    output << "  \"interval_means\": ";
    write_flat_array(output, means);
    output << ",\n";
    output << "  \"interval_stds\": ";
    write_flat_array(output, stds);
    output << ",\n";
    output << "  \"interval_p05\": ";
    write_flat_array(output, percentile_05);
    output << ",\n";
    output << "  \"interval_p95\": ";
    write_flat_array(output, percentile_95);

    if (simulated_prices != nullptr) {
        output << ",\n";
        output << "  \"simulated_prices\": ";
        write_matrix(output, *simulated_prices, simulation_rows, simulation_columns);
    }
    output << "\n";
    output << "}\n";
}

} // namespace

int main(int argc, char **argv) {
    if (argc < 3) {
        std::cerr << "Usage: smartstocks_sim <config_path> <output_path>" << std::endl;
        return 1;
    }

    try {
        const std::string config_path = argv[1];
        const std::string output_path = argv[2];
        Config config = load_config(config_path);

        const std::size_t intervals_per_day = (24 * 60) / std::max<std::size_t>(1, config.interval_minutes);
        const std::size_t total_intervals = config.sim_time * intervals_per_day;
        const double dt = 1.0 / static_cast<double>(intervals_per_day);

        SimulationContext ctx{config,
                              total_intervals,
                              dt,
                              config.bull / static_cast<double>(config.incremental_adjustment_steps),
                              config.bear / static_cast<double>(config.incremental_adjustment_steps),
                              config.average_reduction / static_cast<double>(config.incremental_adjustment_steps)};

        if (total_intervals == 0 || config.num_simulations == 0) {
            throw std::runtime_error("Total intervals and number of simulations must be greater than zero.");
        }

        std::vector<double> results(config.num_simulations * total_intervals, 0.0);
        std::vector<std::thread> workers;
        std::mutex write_mutex;

        const std::size_t hardware_threads = std::thread::hardware_concurrency();
        const std::size_t max_threads = hardware_threads == 0 ? config.threads : std::min(config.threads, hardware_threads);
        const std::size_t threads_to_use = std::max<std::size_t>(1, std::min(max_threads, config.num_simulations));
        const std::size_t base_chunk = config.num_simulations / threads_to_use;
        const std::size_t remainder = config.num_simulations % threads_to_use;

        std::size_t start = 0;
        const bool log_return_interval_mode = config.simulation_mode == "log_return_interval";
        for (std::size_t t = 0; t < threads_to_use; ++t) {
            std::size_t chunk = base_chunk + (t < remainder ? 1 : 0);
            std::size_t end = start + chunk;
            if (log_return_interval_mode) {
                workers.emplace_back(run_log_return_interval_simulations, start, end, std::cref(ctx), std::ref(results));
            } else {
                workers.emplace_back(run_simulations, start, end, std::cref(ctx), std::ref(results), std::ref(write_mutex));
            }
            start = end;
        }

        for (auto &worker : workers) {
            worker.join();
        }

        std::vector<double> means(total_intervals, 0.0);
        for (std::size_t sim = 0; sim < config.num_simulations; ++sim) {
            const std::size_t offset = sim * total_intervals;
            for (std::size_t i = 0; i < total_intervals; ++i) {
                means[i] += results[offset + i];
            }
        }
        for (double &value : means) {
            value /= static_cast<double>(config.num_simulations);
        }

        std::vector<double> stds(total_intervals, 0.0);
        for (std::size_t sim = 0; sim < config.num_simulations; ++sim) {
            const std::size_t offset = sim * total_intervals;
            for (std::size_t i = 0; i < total_intervals; ++i) {
                const double diff = results[offset + i] - means[i];
                stds[i] += diff * diff;
            }
        }
        for (double &value : stds) {
            value = std::sqrt(value / static_cast<double>(config.num_simulations));
        }

        std::vector<double> percentile_05(total_intervals, 0.0);
        std::vector<double> percentile_95(total_intervals, 0.0);
        std::vector<double> workspace(config.num_simulations, 0.0);

        for (std::size_t interval = 0; interval < total_intervals; ++interval) {
            for (std::size_t sim = 0; sim < config.num_simulations; ++sim) {
                workspace[sim] = results[sim * total_intervals + interval];
            }
            std::sort(workspace.begin(), workspace.end());
            percentile_05[interval] = interpolate_percentile(workspace, 0.05);
            percentile_95[interval] = interpolate_percentile(workspace, 0.95);
        }

        if (config.output_simulated_prices) {
            write_output(output_path,
                         means,
                         stds,
                         percentile_05,
                         percentile_95,
                         &results,
                         config.num_simulations,
                         total_intervals);
        } else {
            write_output(output_path, means, stds, percentile_05, percentile_95);
        }
    } catch (const std::exception &ex) {
        std::cerr << "Error: " << ex.what() << std::endl;
        return 1;
    }

    return 0;
}
