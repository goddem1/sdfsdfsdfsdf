import pandas as pd
import numpy as np
from datetime import datetime
import os
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter


class CalculationEngine:
    """
    Движок расчета НМЦК по Приказу Минтранса РФ № 402 от 19.11.2025.
    Использует структуры данных, имитирующие справочники из Excel-файла.
    """

    def __init__(self):
        """
        Инициализирует справочники и константы из Excel-файла.
        """
        self.coefficients = {
            "beta": {
                "Городской": 0.87,
                "Пригородный": 0.91,
                "Межмуниципальный": 0.5,
            },
            "K_pr_ranges": [
                # (min, max) -> K_pr
                ((0, 100000), 0.82),
                ((100001, 300000), 0.79),
                ((300001, 500000), 0.77),
                ((500001, 1000000), 0.755),
                ((1000001, float("inf")), 0.73),
            ],
            "climate": {
                "Умеренная": {"K_to": 1.0, "K_kr": 1.0, "K_zch": 1.0},
                "Умеренно холодная": {"K_to": 0.9, "K_kr": 1.2, "K_zch": 1.25},
                "Холодная": {"K_to": 1.2, "K_kr": 1.25, "K_zch": 1.25},
            },
            "normatives_fuel": {
                # Лист 8, Таблица 4: Нормативы расхода топлива (л/100км)
                "Особо малый": {
                    "Бензин": (13, 18),
                    "Дизель": (11, 15),
                    "Газ": (16, 22),
                    "Электро": 0,
                },
                "Малый": {
                    "Бензин": (17, 22),
                    "Дизель": (15, 20),
                    "Газ": (20, 26),
                    "Электро": 0,
                },
                "Средний": {
                    "Бензин": (25, 30),
                    "Дизель": (22, 27),
                    "Газ": (30, 36),
                    "Электро": 0,
                },
                "Большой": {
                    "Бензин": (30, 36),
                    "Дизель": (27, 33),
                    "Газ": (36, 43),
                    "Электро": 0,
                },
                "Особо большой": {
                    "Бензин": (35, 42),
                    "Дизель": (32, 38),
                    "Газ": (42, 50),
                    "Электро": 0,
                },
            },
            "normatives_tyres_parts": {
                # Лист 8, Таблица 6: Нормативы шины и запчасти (руб/км, базовые 2019г)
                "Особо малый": {"U_shini": 0.15, "U_zapchasti": 1.8},
                "Малый": {"U_shini": 0.28, "U_zapchasti": 3.2},
                "Средний": {"U_shini": 0.45, "U_zapchasti": 5.5},
                "Большой": {"U_shini": 0.6, "U_zapchasti": 7.2},
                "Особо большой": {"U_shini": 0.75, "U_zapchasti": 9.0},
            },
            "normatives_to_repair": {
                # Лист 8, Таблица 7: Трудоемкость ТО и ремонта (ч/1000км)
                "Особо малый": {"T_to": 5, "T_remont": 4},
                "Малый": {"T_to": 8, "T_remont": 6.4},
                "Средний": {"T_to": 12, "T_remont": 9.6},
                "Большой": {"T_to": 15, "T_remont": 12},
                "Особо большой": {"T_to": 18, "T_remont": 14.4},
            },
            "normatives_resource": {
                # Лист 8, Таблица 8: Нормативный ресурс ТС до списания (км)
                "Особо малый": 400000,
                "Малый": 640000,
                "Средний": 750000,
                "Большой": 900000,
                "Особо большой": 1000000,
            },
        }
        self.constants = {
            "lubricant_norm_pct": 0.075,  # 7.5% от расхода топлива (Лист 4.1)
            "social_contribution_rate_default": 30.8,  # (Лист 1, D47)
            "FRV_driver_hours_per_year": 1772,  # (Лист 2.1)
            "FRV_repairer_hours_per_year": 1812,  # (Лист 5.1)
            "R_default": 1.096,  # (Лист 1, D3)
            "ZP_reg_avg": 87133,  # Средняя зарплата по региону (Лист 2.1, D4)
            "ZPR_avg": 87154.3,  # Средняя зарплата ремонтников (Лист 5.1, D4)
            "fuel_price": 65.4,  # Цена топлива (Лист 3, D4)
        }

    def calculate(self, input_data):
        """
        Выполняет расчет НМЦК на основе входных данных.

        Args:
            input_data (dict): Словарь с входными параметрами из формы.

        Returns:
            dict: Словарь с результатами расчета и детальной логикой.
        """
        try:
            # Инициализируем список для хранения шагов расчета
            calculation_steps = []

            # --- Извлечение данных из input_data ---
            # Блок 1
            L_ti = float(input_data["contractRun"])
            calculation_steps.append(
                {
                    "Этап": "Входные данные",
                    "Параметр": "Плановый пробег (L_ti)",
                    "Значение": f"{L_ti:,.0f}",
                    "Формула": "Из формы ввода",
                    "Результат": f"{L_ti:,.0f} км/мес",
                }
            )

            N_ijt = int(input_data["mainVehicles"])
            calculation_steps.append(
                {
                    "Этап": "Входные данные",
                    "Параметр": "Основные ТС (N_ijt)",
                    "Значение": f"{N_ijt}",
                    "Формула": "Из формы ввода",
                    "Результат": f"{N_ijt} ед.",
                }
            )

            N_res_input = input_data.get("reserveVehicles")
            if N_res_input is not None and N_res_input != "":
                N_res = int(N_res_input)
                res_formula = "Введено вручную"
            else:
                # Рассчитать N_res по логике из Excel (Лист 1, строка 9)
                if N_ijt == 1:
                    N_res = 1
                    res_formula = "N_res = 1 (при N_ijt = 1)"
                else:
                    N_res = max(1, N_ijt // 10)
                    res_formula = (
                        f"N_res = max(1, {N_ijt} // 10) = max(1, {N_ijt//10}) = {max(1, N_ijt//10)}"
                    )

            calculation_steps.append(
                {
                    "Этап": "Входные данные",
                    "Параметр": "Резервные ТС (N_res)",
                    "Значение": f"{N_res}",
                    "Формула": res_formula,
                    "Результат": f"{N_res} ед.",
                }
            )

            M_Sijt = N_ijt + N_res
            calculation_steps.append(
                {
                    "Этап": "Расчет",
                    "Параметр": "Всего ТС (M_Sijt)",
                    "Значение": f"{M_Sijt}",
                    "Формула": f"M_Sijt = N_ijt + N_res = {N_ijt} + {N_res}",
                    "Результат": f"{M_Sijt} ед.",
                }
            )

            r_months = int(input_data["contractPeriod"])
            calculation_steps.append(
                {
                    "Этап": "Входные данные",
                    "Параметр": "Срок контракта (r_months)",
                    "Значение": f"{r_months}",
                    "Формула": "Из формы ввода",
                    "Результат": f"{r_months} мес.",
                }
            )

            P_t = float(input_data["plannedFare"])
            calculation_steps.append(
                {
                    "Этап": "Входные данные",
                    "Параметр": "Плановый тариф (P_t)",
                    "Значение": f"{P_t:,.2f}",
                    "Формула": "Из формы ввода",
                    "Результат": f"{P_t:,.2f} руб.",
                }
            )

            C_sub = float(input_data["subsidies"])
            calculation_steps.append(
                {
                    "Этап": "Входные данные",
                    "Параметр": "Субсидии (C_sub)",
                    "Значение": f"{C_sub:,.2f}",
                    "Формула": "Из формы ввода",
                    "Результат": f"{C_sub:,.2f} руб.",
                }
            )

            vehicle_class = input_data["vehicleClass"]
            route_type = input_data["routeType"]
            climate_zone = input_data["climateZone"]
            fuel_type = input_data["fuelType"]
            seating_capacity = int(input_data["seatingCapacity"])
            vehicle_price = float(input_data["vehiclePrice"])
            service_life_years = int(input_data["serviceLife"])

            # Блок 2
            R = float(input_data.get("profitabilityLevel", self.constants["R_default"]))

            L_ci_input = input_data.get("resourceUntilWriteOff")
            C_oi = float(input_data.get("additionalEquipmentCost", 0))

            # Блок 3
            I_pct = float(input_data["consumerPriceIndex"])
            I_tt = float(input_data["fuelPriceIndex"])
            I_mt = float(input_data["equipmentPriceIndex"])

            # Блок 4
            k_pz = float(input_data.get("prepCloseTimeCoeff", 1.0))
            K_pr_input = input_data.get("otherExpensesCoeff")
            K_zpi = float(input_data["driverSalaryCoeff"])
            k_bill = float(input_data["ticketFunctionCoeff"])
            St_c_pct = float(
                input_data.get(
                    "socialContributionRate", self.constants["social_contribution_rate_default"]
                )
            )
            D_pct = float(input_data.get("fuelConsumptionCorrection", 0))

            # --- Подстановка значений из справочников ---
            beta = self.coefficients["beta"].get(route_type, 0.91)

            # K_to
            if "K_to" in input_data and input_data["K_to"] != "":
                K_to = float(input_data["K_to"])
            else:
                climate_coeffs = self.coefficients["climate"].get(
                    climate_zone, {"K_to": 1.0, "K_kr": 1.0, "K_zch": 1.0}
                )
                K_to = climate_coeffs["K_to"]

            # K_kr
            if "K_kr" in input_data and input_data["K_kr"] != "":
                K_kr = float(input_data["K_kr"])
            else:
                climate_coeffs = self.coefficients["climate"].get(
                    climate_zone, {"K_to": 1.0, "K_kr": 1.0, "K_zch": 1.0}
                )
                K_kr = climate_coeffs["K_kr"]

            # K_zch
            if "K_zch" in input_data and input_data["K_zch"] != "":
                K_zch = float(input_data["K_zch"])
            else:
                climate_coeffs = self.coefficients["climate"].get(
                    climate_zone, {"K_to": 1.0, "K_kr": 1.0, "K_zch": 1.0}
                )
                K_zch = climate_coeffs["K_zch"]

            # Нормативы U_shini, U_zapchasti
            normatives_tp = self.coefficients["normatives_tyres_parts"].get(
                vehicle_class, {"U_shini": 0.28, "U_zapchasti": 3.2}
            )
            U_shini = normatives_tp["U_shini"]
            U_zapchasti = normatives_tp["U_zapchasti"]

            # Нормативы T_to, T_remont
            normatives_tr = self.coefficients["normatives_to_repair"].get(
                vehicle_class, {"T_to": 8, "T_remont": 6.4}
            )
            T_to_norm = normatives_tr["T_to"]
            T_remont_norm = normatives_tr["T_remont"]

            # Норматив L_ci (ресурс)
            if L_ci_input is not None and L_ci_input != "":
                L_ci = float(L_ci_input)
            else:
                L_ci = self.coefficients["normatives_resource"].get(vehicle_class, 640000)

            # Норма расхода топлива H_si
            fuel_norm_range = self.coefficients["normatives_fuel"].get(vehicle_class, {}).get(
                fuel_type, (0, 0)
            )
            if fuel_norm_range != (0, 0):
                if isinstance(fuel_norm_range, tuple):
                    H_si = sum(fuel_norm_range) / 2
                else:
                    H_si = fuel_norm_range
            else:
                H_si = 17

            # --- Расчеты ---
            ZP_reg_avg = self.constants["ZP_reg_avg"]
            ZPV_i = ZP_reg_avg * K_zpi
            k_otpu = 1.0
            ACH_ti = 182
            FRV_v = self.constants["FRV_driver_hours_per_year"]

            # 1. P_OTVti
            P_OTVti = (12 * ZPV_i * k_otpu * ACH_ti * k_pz * I_pct) / (L_ti * FRV_v)

            # 2. P_OTKti
            P_OTKti = P_OTVti * k_bill

            # 3. SR_ti
            SR_ti = (P_OTVti + P_OTKti) * (St_c_pct / 100)

            # 4. Топливо (P_Tti)
            fuel_price = self.constants["fuel_price"]
            H_ot = 0
            V_e = 61.667
            N_z = 1
            P_Tti = (
                fuel_price
                * (H_si / 100 * (1 + D_pct / 100) + H_ot / V_e * N_z / 12)
                * I_tt
            )

            # 5. Смазочные материалы (P_SMti)
            P_SMti = P_Tti * self.constants["lubricant_norm_pct"]

            # 6. Шины (P_Shti)
            P_Shti = U_shini * I_mt

            # 7. ТО и ремонт (P_TOti)
            ZPR_avg = self.constants["ZPR_avg"]
            FRV_rr = self.constants["FRV_repairer_hours_per_year"]

            FOT_rr_i = (
                (12 * ZPR_avg / FRV_rr)
                * I_pct
                * (T_to_norm / K_to + T_remont_norm * K_kr)
                * 0.001
                * (1 + St_c_pct / 100)
            )

            # 7.2. Запчасти (РЗЧ_ti)
            RZCH_ti = U_zapchasti * K_zch * I_mt

            # 7.3. Итого ТО и ремонт (P_TOti)
            P_TOti = FOT_rr_i + RZCH_ti

            # 8. Прочие и косвенные (PKR_ti)
            if K_pr_input is not None and K_pr_input != "":
                K_pr = float(K_pr_input)
            else:
                total_annual_run = L_ti * M_Sijt * (12 / r_months)
                K_pr = None
                for (min_val, max_val), coeff in self.coefficients["K_pr_ranges"]:
                    if min_val <= total_annual_run <= max_val:
                        K_pr = coeff
                        break
                if K_pr is None:
                    raise ValueError(
                        f"Не удалось определить K_pr для общего годового пробега {total_annual_run}"
                    )

            base_for_Kpr = P_Tti + P_SMti + P_Shti + P_TOti
            PKR_ti = K_pr * base_for_Kpr

            # 9. Амортизация доп. оборудования (P_oi)
            if r_months > 0:
                P_oi = C_oi / (L_ci * (r_months / 12))
            else:
                P_oi = 0

            # 10. Аренда (РП_ijt)
            RP_ijt = 0.0

            # --- ИТОГО C (руб./км) ---
            C = (
                P_OTVti
                + P_OTKti
                + SR_ti
                + P_Tti
                + P_SMti
                + P_Shti
                + P_TOti
                + PKR_ti
                + P_oi
                + RP_ijt
            )

            # --- Расчет НМЦК ---
            nmck_value = C * R * L_ti * M_Sijt - P_t - C_sub

            results = {
                "success": True,
                "summary": {
                    "cost_per_km": round(C, 6),
                    "nmck_total": round(nmck_value, 2),
                    "total_vehicles": M_Sijt,
                    "annual_run": round(L_ti * M_Sijt * (12 / r_months), 2),
                    "K_pr_used": K_pr,
                },
                "details": {
                    "P_OTVti": round(P_OTVti, 6),
                    "P_OTKti": round(P_OTKti, 6),
                    "SR_ti": round(SR_ti, 6),
                    "P_Tti": round(P_Tti, 6),
                    "P_SMti": round(P_SMti, 6),
                    "P_Shti": round(P_Shti, 6),
                    "P_TOti": round(P_TOti, 6),
                    "PKR_ti": round(PKR_ti, 6),
                    "P_oi": round(P_oi, 6),
                    "RP_ijt": round(RP_ijt, 6),
                },
                "calculation_steps": calculation_steps,
                "input_data_used": {
                    "L_ti": L_ti,
                    "M_Sijt": M_Sijt,
                    "R": R,
                    "P_t": P_t,
                    "C_sub": C_sub,
                    "K_pr": K_pr,
                    "vehicle_class": vehicle_class,
                    "route_type": route_type,
                    "fuel_type": fuel_type,
                    "climate_zone": climate_zone,
                },
            }
            return results

        except KeyError as e:
            return {"success": False, "error": f"Отсутствует обязательное поле ввода: {e}"}
        except ValueError as e:
            return {"success": False, "error": f"Ошибка в значении поля ввода: {e}"}
        except ZeroDivisionError as e:
            return {"success": False, "error": f"Ошибка деления на ноль: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Непредвиденная ошибка при расчете: {e}"}

    def save_results_to_excel(self, results, filename=None):
        """
        Сохраняет результаты расчета в Excel файл с детальной логикой и форматированием.
        """
        try:
            if not results.get("success", False):
                print("Нет результатов для сохранения")
                return None

            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"nmck_calculation_{timestamp}.xlsx"

            with pd.ExcelWriter(filename, engine="openpyxl") as writer:
                summary_data = {
                    "Показатель": [
                        "Себестоимость 1 км (C)",
                        "НМЦК всего",
                        "Всего ТС",
                        "Годовой пробег",
                        "Коэффициент K_pr",
                    ],
                    "Значение": [
                        results["summary"]["cost_per_km"],
                        results["summary"]["nmck_total"],
                        results["summary"]["total_vehicles"],
                        results["summary"]["annual_run"],
                        results["summary"]["K_pr_used"],
                    ],
                    "Ед. измерения": ["руб/км", "руб", "ед.", "км/год", ""],
                }
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name="Сводка", index=False)

                details_data = {
                    "Статья расходов": [
                        "ФОТ водителей",
                        "ФОТ кондукторов",
                        "Социальные отчисления",
                        "Топливо",
                        "Смазочные материалы",
                        "Шины",
                        "ТО и ремонт",
                        "Прочие и косвенные",
                        "Амортизация доп. оборудования",
                        "Аренда",
                    ],
                    "Обозначение": [
                        "P_OTVti",
                        "P_OTKti",
                        "SR_ti",
                        "P_Tti",
                        "P_SMti",
                        "P_Shti",
                        "P_TOti",
                        "PKR_ti",
                        "P_oi",
                        "RP_ijt",
                    ],
                    "Значение (руб/км)": [
                        results["details"]["P_OTVti"],
                        results["details"]["P_OTKti"],
                        results["details"]["SR_ti"],
                        results["details"]["P_Tti"],
                        results["details"]["P_SMti"],
                        results["details"]["P_Shti"],
                        results["details"]["P_TOti"],
                        results["details"]["PKR_ti"],
                        results["details"]["P_oi"],
                        results["details"]["RP_ijt"],
                    ],
                }
                df_details = pd.DataFrame(details_data)
                df_details.to_excel(writer, sheet_name="Детальные расходы", index=False)

                input_data_list = []
                for key, value in results["input_data_used"].items():
                    input_data_list.append({"Параметр": key, "Значение": value})
                df_input = pd.DataFrame(input_data_list)
                df_input.to_excel(writer, sheet_name="Входные данные", index=False)

                if "calculation_steps" in results and results["calculation_steps"]:
                    df_steps = pd.DataFrame(results["calculation_steps"])
                    df_steps.to_excel(writer, sheet_name="Логика расчета", index=False)

                ref_data = []
                ref_data.append(
                    {
                        "Справочник": "Климатические коэффициенты",
                        "Параметр": f"K_to для {results['input_data_used'].get('climate_zone', 'неизвестно')}",
                        "Значение": self.get_climate_coeff(
                            results["input_data_used"].get("climate_zone", ""), "K_to"
                        ),
                    }
                )
                ref_data.append(
                    {
                        "Справочник": "Климатические коэффициенты",
                        "Параметр": f"K_kr для {results['input_data_used'].get('climate_zone', 'неизвестно')}",
                        "Значение": self.get_climate_coeff(
                            results["input_data_used"].get("climate_zone", ""), "K_kr"
                        ),
                    }
                )
                ref_data.append(
                    {
                        "Справочник": "Климатические коэффициенты",
                        "Параметр": f"K_zch для {results['input_data_used'].get('climate_zone', 'неизвестно')}",
                        "Значение": self.get_climate_coeff(
                            results["input_data_used"].get("climate_zone", ""), "K_zch"
                        ),
                    }
                )
                df_ref = pd.DataFrame(ref_data)
                df_ref.to_excel(writer, sheet_name="Справочники", index=False)

            return filename

        except Exception as e:
            print(f"Ошибка при сохранении в Excel: {e}")
            import traceback

            traceback.print_exc()
            return None

    def get_climate_coeff(self, climate_zone, coeff_name):
        """Вспомогательный метод для получения климатических коэффициентов."""
        if climate_zone in self.coefficients["climate"]:
            return self.coefficients["climate"][climate_zone].get(coeff_name, 1.0)
        return 1.0

