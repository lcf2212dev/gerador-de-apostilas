#!/usr/bin/env python3
"""Testes de `sumario.py` e `ler_grafo.py`.

    python3 .claude/skills/montar-sumario/scripts/testes/test_sumario.py

Cobrem o que quebra em silêncio: ordem que viola pré-requisito, nota que não reage à
incidência, grafo com ciclo, grafo pobre em dados, a regra de lastro julgando (ou não)
quem não tem questões, e o `conferir` deixando passar uma grade errada. Não testam
gosto (nome de módulo, redação) — isso é do revisor humano.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))

import ler_grafo  # noqa: E402
import sumario    # noqa: E402
from ler_grafo import Aresta, Grafo, No  # noqa: E402

FIXTURE = AQUI / "grafo-exemplo.md"


def grafo_sintetico(nos: list[tuple], arestas: list[tuple] = ()) -> Grafo:
    """nos: (id, pai, nivel, peso, share_pct, n_questoes, custo_h). arestas: (de, para, tipo)."""
    mapa = {}
    for nid, pai, nivel, peso, share, nq, custo in nos:
        mapa[nid] = No(id=nid, rotulo=nid.replace("-", " ").title(), pai=pai, nivel=nivel,
                       peso=peso, share_pct=share, n_questoes=nq, custo_h=custo, edital=1.0,
                       confianca=0.9, classe="A")
    return Grafo(nos=mapa, arestas=[Aresta(d, p, t, 1.0) for d, p, t in arestas],
                 meta={"escopo": "Sintético"}, parametros={}, lacunas_de_origem=[],
                 origem="memória", sha256="0" * 64, fonte="teste")


def calar(fn, *a, **kw):
    """Roda silenciando stderr — `erro()` escreve lá antes de levantar SystemExit."""
    with contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **kw)


class TestLeitura(unittest.TestCase):
    def test_le_o_grafo_md_do_motor(self):
        g = ler_grafo.carregar(FIXTURE)
        self.assertEqual(g.fonte, "grafo.md")
        self.assertEqual(len(g.nos), 23)
        self.assertEqual(len(g.arestas), 18)
        self.assertEqual(g.meta["escopo"], "Direito Constitucional")
        self.assertEqual(g.meta["ano_ref"], 2026)          # inteiro, não 2026.0
        self.assertEqual(g.nos["dc-dir-ind"].peso, 100)
        self.assertIsNone(g.nos["dc"].pai)
        self.assertEqual(g.nos["dc-dir-ind"].pai, "dc-dir")

    def test_todos_os_campos_chegam(self):
        g = ler_grafo.carregar(FIXTURE)
        for campo, fracao in ler_grafo.cobertura_de_campos(g).items():
            self.assertEqual(fracao, 1.0, f"campo {campo} incompleto")

    def test_a_secao_de_prioridades_nao_duplica_nem_apaga_o_nivel(self):
        # a seção 2 do grafo.md repete as folhas sem `nível`/`pai`; a seção 3 é a completa
        g = ler_grafo.carregar(FIXTURE)
        self.assertEqual(g.nos["dc-dir-ind"].nivel, "topico")

    def test_mermaid(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "g.md"
            p.write_text("```mermaid\ngraph TD\n"
                         '  a["Base (30 questões)"]\n'
                         '  b["Avançado (90 questões)"]\n'
                         "  a -->|requer| b\n"
                         "  a -.->|0.4| b\n```\n", encoding="utf-8")
            g = ler_grafo.carregar(p)
        self.assertEqual(g.fonte, "generico")
        self.assertEqual(g.nos["a"].n_questoes, 30)
        self.assertEqual({a.tipo for a in g.arestas}, {"prerequisito", "correlato"})

    def test_lista_aninhada(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "g.md"
            p.write_text("- Direito Penal\n"
                         "  - [[Teoria do Crime]] (120 questões)\n"
                         "  - [[Penas]] (60 questões)\n"
                         "    - requer: [[Teoria do Crime]]\n", encoding="utf-8")
            g = ler_grafo.carregar(p)
        self.assertEqual(g.nos["penas"].pai, "direito-penal")
        self.assertEqual(g.nos["teoria-do-crime"].n_questoes, 120)
        self.assertIn(("teoria-do-crime", "penas", "prerequisito"),
                      [(a.de, a.para, a.tipo) for a in g.arestas])

    def test_arquivo_ilegivel_explica_os_formatos(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "g.md"
            p.write_text("# só um título e prosa solta\n", encoding="utf-8")
            with self.assertRaises(ler_grafo.ErroDeLeitura) as ctx:
                ler_grafo.carregar(p)
        self.assertIn("mermaid", str(ctx.exception))


MOTOR = AQUI.parents[4] / ler_grafo.CAMINHO_MOTOR  # raiz do repo, derivada do próprio arquivo
FIXTURE_MOTOR = AQUI / "motor-exemplo"


@unittest.skipUnless(MOTOR.is_file(), "a skill mapear-conteudo não está instalada")
class TestIntegracaoComOMotor(unittest.TestCase):
    """Contrato com a skill que gera o grafo. Se ela mudar o schema, estes testes caem —
    e é isso que se quer: a quebra aparece aqui, não num sumário com número errado."""

    def test_le_evidencias_pelo_motor(self):
        g = ler_grafo.carregar(FIXTURE_MOTOR)
        self.assertEqual(g.fonte, "motor")
        self.assertEqual(len(g.nos), 4)
        for campo in ("peso", "classe", "share_pct", "n_questoes", "edital", "confianca",
                      "custo_h", "nivel"):
            self.assertEqual(ler_grafo.cobertura_de_campos(g)[campo], 1.0,
                             f"o motor parou de entregar {campo}")

    def test_direcao_do_prerequisito_continua_de_pre_para_dependente(self):
        g = ler_grafo.carregar(FIXTURE_MOTOR)
        pre = [(a.de, a.para) for a in g.arestas if a.tipo == "prerequisito"]
        self.assertIn(("da-princ", "da-atos"), pre)
        plano = sumario.priorizar(g, "Direito Administrativo", {})
        atos = next(i for i in plano["itens"] if i["id"] == "da-atos")
        self.assertIn("da-princ", atos["requer"])

    def test_plano_completo_a_partir_de_evidencias(self):
        plano = sumario.priorizar(ler_grafo.carregar(FIXTURE_MOTOR), "Direito Administrativo", {})
        self.assertEqual(len(plano["itens"]), 3)
        self.assertEqual(plano["grafo"]["fonte"], "motor")
        self.assertEqual(plano["grafo"]["banca_alvo"], ["FGV"])
        self.assertTrue(plano["lacunas"]["do_grafo"], "as lacunas do grafo têm que ser herdadas")


class TestPriorizacao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = ler_grafo.carregar(FIXTURE)
        cls.plano = sumario.priorizar(cls.g, "Direito Constitucional", {"data": "2026-01-01"})

    def test_determinismo(self):
        outro = sumario.priorizar(ler_grafo.carregar(FIXTURE), "Direito Constitucional",
                                  {"data": "2026-01-01"})
        self.assertEqual(json.dumps(self.plano, sort_keys=True),
                         json.dumps(outro, sort_keys=True))

    def test_ordem_respeita_prerequisitos(self):
        seq = {i["id"]: i["seq"] for i in self.plano["itens"]}
        for item in self.plano["itens"]:
            for pre in item["requer"]:
                self.assertLess(seq[pre], item["seq"],
                                f"{item['id']} veio antes do pré-requisito {pre}")

    def test_todo_item_tem_nota_de_1_a_10(self):
        for item in self.plano["itens"]:
            self.assertIn(item["importancia"], range(1, 11))
        notas = {i["importancia"] for i in self.plano["itens"]}
        self.assertEqual(max(notas), 10, "o topo do recorte tem que valer 10")
        self.assertGreater(len(notas), 3, "escada achatada demais para ser útil")

    def test_o_topo_da_escada_e_o_de_maior_valor(self):
        topo = max(self.plano["itens"], key=lambda i: i["valor"])
        self.assertEqual(topo["importancia"], 10)
        self.assertEqual(topo["id"], "dc-dir-ind")

    def test_cobertura_fecha_em_cem_por_cento(self):
        self.assertAlmostEqual(self.plano["cobertura"]["curva"][-1]["acumulado"], 1.0, places=3)
        self.assertLessEqual(self.plano["lacunas"]["share_nao_coberto"], 0.001)

    def test_curva_traz_o_que_ainda_falta(self):
        for ponto in self.plano["cobertura"]["curva"]:
            self.assertAlmostEqual(ponto["acumulado"] + ponto["restante"], 1.0, places=3)

    def test_marcos_sao_crescentes(self):
        marcos = [v for v in self.plano["cobertura"]["marcos"].values() if v]
        self.assertEqual(marcos, sorted(marcos))

    def test_modulos_cobrem_todos_os_itens_uma_vez(self):
        dos_modulos = [i for m in self.plano["modulos"] for i in m["itens"]]
        self.assertEqual(sorted(dos_modulos), sorted(i["id"] for i in self.plano["itens"]))

    def test_horas_e_aulas_batem(self):
        for item in self.plano["itens"]:
            self.assertEqual(sum(item["minutos_por_aula"]), item["minutos"])
            self.assertEqual(len(item["minutos_por_aula"]), item["aulas"])
            for minutos in item["minutos_por_aula"]:
                self.assertLessEqual(minutos, sumario.PADROES["minutos_max"])
            # a regra de lastro amarra o formato ao fatiamento
            if item["formato"] == "curta":
                self.assertEqual(item["aulas"], 1)
                self.assertLessEqual(item["minutos"], sumario.PADROES["minutos_max_curta"])
            elif item["formato"] == "opcional":
                self.assertEqual(item["aulas"], 0)
                self.assertEqual(item["minutos"], 0)

    def test_recorte_por_tema_importa_prerequisitos_para_o_modulo_zero(self):
        plano = sumario.priorizar(self.g, "Controle de Constitucionalidade", {})
        importados = {i["id"] for i in plano["itens"] if "importado" in i["marcas"]}
        self.assertEqual(importados, {"dc-fund-obj", "dc-dir-ind", "dc-pod-jud"})
        base = next(m for m in plano["modulos"] if m["num"] == 0)
        self.assertEqual(set(base["itens"]), importados)
        self.assertAlmostEqual(sum(i["share"] for i in plano["itens"]), 1.0, places=3)

    def test_sem_prerequisitos_nao_importa_nada(self):
        plano = sumario.priorizar(self.g, "Controle de Constitucionalidade", {},
                                  importar_prereq=False)
        self.assertEqual(len(plano["itens"]), 3)
        self.assertEqual(plano["lacunas"]["importados"], [])


class TestSinais(unittest.TestCase):
    def test_centralidade_premia_quem_destrava(self):
        # dois itens de incidência idêntica: um é pré-requisito do item pesado, o outro não
        g = grafo_sintetico(
            [("raiz", None, "disciplina", 100, 100.0, 200, 6.0),
             ("porta", "raiz", "topico", 20, 10.0, 20, 1.0),
             ("isolado", "raiz", "topico", 20, 10.0, 20, 1.0),
             ("pesado", "raiz", "topico", 100, 80.0, 160, 4.0)],
            [("porta", "pesado", "prerequisito")])
        plano = sumario.priorizar(g, "raiz", {})
        nota = {i["id"]: i["importancia"] for i in plano["itens"]}
        self.assertGreater(nota["porta"], nota["isolado"],
                           "quem destrava o tópico pesado tem que valer mais")

    def test_mais_questoes_nunca_baixa_a_nota(self):
        base = [("raiz", None, "disciplina", 100, 100.0, 300, 6.0),
                ("a", "raiz", "topico", 50, 30.0, 90, 2.0),
                ("b", "raiz", "topico", 50, 30.0, 90, 2.0),
                ("c", "raiz", "topico", 60, 40.0, 120, 2.0)]
        antes = sumario.priorizar(grafo_sintetico(base), "raiz", {})
        subiu = [(nid, p, n, peso if nid != "a" else 90, share, nq, custo)
                 for nid, p, n, peso, share, nq, custo in base]
        depois = sumario.priorizar(grafo_sintetico(subiu), "raiz", {})
        nota = lambda plano, i: next(x["importancia"] for x in plano["itens"] if x["id"] == i)
        self.assertGreaterEqual(nota(depois, "a"), nota(antes, "a"))

    def test_esforco_nao_entra_na_nota_so_na_fila(self):
        g = grafo_sintetico(
            [("raiz", None, "disciplina", 100, 100.0, 200, 10.0),
             ("caro", "raiz", "topico", 100, 50.0, 100, 8.0),
             ("barato", "raiz", "topico", 100, 50.0, 100, 1.0)])
        plano = sumario.priorizar(g, "raiz", {})
        notas = {i["id"]: i["importancia"] for i in plano["itens"]}
        self.assertEqual(notas["caro"], notas["barato"], "a nota mede valor, não facilidade")
        seq = {i["id"]: i["seq"] for i in plano["itens"]}
        self.assertLess(seq["barato"], seq["caro"], "o ROI decide a ordem")

    def test_niveis_mistos_trocam_a_base_de_valor(self):
        g = grafo_sintetico(
            [("raiz", None, "disciplina", 100, 100.0, 200, 4.0),
             ("t", "raiz", "tema", 100, 60.0, 120, 2.0),
             ("s", "raiz", "subtopico", 100, 40.0, 80, 2.0)])
        plano = sumario.priorizar(g, "raiz", {})
        self.assertEqual(plano["parametros"]["base_de_valor"], "share+edital")
        self.assertTrue(any("níveis diferentes" in a
                            for a in plano["lacunas"]["avisos_do_calculo"]))

    def test_grafo_sem_numero_nenhum_degrada_e_avisa(self):
        g = grafo_sintetico([("raiz", None, None, None, None, None, None),
                             ("a", "raiz", None, None, None, None, None),
                             ("b", "raiz", None, None, None, None, None)])
        for n in g.nos.values():
            n.edital = None
            n.confianca = None
        plano = sumario.priorizar(g, "raiz", {})
        self.assertEqual(plano["parametros"]["base_de_valor"], "uniforme")
        self.assertEqual(len(plano["itens"]), 2)
        self.assertTrue(plano["lacunas"]["custo_estimado"])
        self.assertIn("centralidade", plano["lacunas"]["sinais_desligados"])

    def test_ciclo_de_prerequisito_nao_trava(self):
        g = grafo_sintetico(
            [("raiz", None, "disciplina", 100, 100.0, 200, 4.0),
             ("a", "raiz", "topico", 60, 50.0, 100, 2.0),
             ("b", "raiz", "topico", 40, 50.0, 100, 2.0)],
            [("a", "b", "prerequisito"), ("b", "a", "prerequisito")])
        plano = sumario.priorizar(g, "raiz", {})
        self.assertEqual(len(plano["itens"]), 2)
        self.assertTrue(plano["lacunas"]["ciclos"], "o ciclo tem que ser reportado")


class TestLastro(unittest.TestCase):
    """Incidência é pré-condição de aula cheia: sem 4 questões e sem 2% do share, o
    item vira aula curta (edital ou dependente cheio) ou opcional (nem isso)."""

    def grafo_com_item_vazio(self) -> Grafo:
        return grafo_sintetico(
            [("raiz", None, "disciplina", 100, 100.0, 200, 6.0),
             ("forte", "raiz", "topico", 100, 95.0, 196, 4.0),
             ("vazio", "raiz", "topico", 5, 0.0, 0, 2.0)])

    def test_item_sem_questoes_com_edital_vira_aula_curta(self):
        plano = sumario.priorizar(self.grafo_com_item_vazio(), "raiz", {})
        vazio = next(i for i in plano["itens"] if i["id"] == "vazio")
        self.assertEqual(vazio["formato"], "curta")
        self.assertEqual(vazio["aulas"], 1, "aula curta é exatamente 1 aula")
        self.assertLessEqual(vazio["minutos"], sumario.PADROES["minutos_max_curta"])
        self.assertGreaterEqual(vazio["minutos"], sumario.PADROES["minutos_min"])
        self.assertIn("sem-lastro", vazio["marcas"])
        forte = next(i for i in plano["itens"] if i["id"] == "forte")
        self.assertEqual(forte["formato"], "cheia")
        self.assertEqual(plano["totais"]["aulas_curtas"], 1)

    def test_item_sem_lastro_sem_edital_sem_dependente_vira_opcional(self):
        g = self.grafo_com_item_vazio()
        g.nos["vazio"].edital = 0.0
        plano = sumario.priorizar(g, "raiz", {})
        vazio = next(i for i in plano["itens"] if i["id"] == "vazio")
        self.assertEqual(vazio["formato"], "opcional")
        self.assertEqual(vazio["aulas"], 0)
        self.assertEqual(vazio["minutos"], 0)
        self.assertIn("opcional", vazio["motivo_omissao"])
        self.assertIn("sem-lastro", vazio["marcas"])
        self.assertEqual(plano["totais"]["itens_opcionais"], 1)

    def test_prerequisito_de_item_cheio_vira_curta_mesmo_sem_edital(self):
        g = grafo_sintetico(
            [("raiz", None, "disciplina", 100, 100.0, 200, 6.0),
             ("porta", "raiz", "topico", 5, 0.0, 0, 2.0),
             ("forte", "raiz", "topico", 100, 95.0, 196, 4.0)],
            [("porta", "forte", "prerequisito")])
        g.nos["porta"].edital = 0.0
        plano = sumario.priorizar(g, "raiz", {})
        porta = next(i for i in plano["itens"] if i["id"] == "porta")
        self.assertEqual(porta["formato"], "curta", "quem destrava item cheio não some")

    def test_grafo_sem_incidencia_desliga_a_regra_com_aviso(self):
        g = grafo_sintetico([("raiz", None, None, None, None, None, None),
                             ("a", "raiz", None, None, None, None, None),
                             ("b", "raiz", None, None, None, None, None)])
        plano = sumario.priorizar(g, "raiz", {})
        self.assertFalse(plano["parametros"]["lastro_aplicado"])
        self.assertTrue(all(i["formato"] == "cheia" for i in plano["itens"]))
        self.assertEqual(plano["totais"]["itens_opcionais"], 0)
        self.assertTrue(all("sem-lastro" not in i["marcas"] for i in plano["itens"]))
        self.assertTrue(any("a regra de lastro não julga ninguém" in a
                            for a in plano["lacunas"]["avisos_do_calculo"]))

    def test_sem_lastro_restaura_o_comportamento_antigo(self):
        g = self.grafo_com_item_vazio()
        g.nos["vazio"].edital = 0.0
        plano = sumario.priorizar(g, "raiz", {}, sem_lastro=True)
        vazio = next(i for i in plano["itens"] if i["id"] == "vazio")
        self.assertEqual(vazio["formato"], "cheia")
        self.assertEqual(vazio["minutos"], 120, "custo_h de 2 h volta a valer inteiro")
        self.assertEqual(vazio["aulas"], 4)
        self.assertIn("sem-lastro", vazio["marcas"], "a promoção sem lastro fica marcada")
        self.assertFalse(plano["parametros"]["lastro_aplicado"])
        self.assertTrue(plano["parametros"]["sem_lastro"])
        self.assertTrue(any("--sem-lastro" in a
                            for a in plano["lacunas"]["avisos_do_calculo"]))


class TestAssunto(unittest.TestCase):
    def setUp(self):
        self.g = ler_grafo.carregar(FIXTURE)

    def test_casa_por_id_rotulo_e_aproximacao(self):
        self.assertEqual(calar(sumario.resolver_assunto, self.g, "dc-con"), "dc-con")
        self.assertEqual(calar(sumario.resolver_assunto, self.g, "poder judiciário"), "dc-pod-jud")
        self.assertEqual(calar(sumario.resolver_assunto, self.g, "Controle de Constitucionalidade"),
                         "dc-con")

    def test_escopo_inteiro_vira_a_raiz_e_nao_um_modulo_so(self):
        self.assertEqual(calar(sumario.resolver_assunto, self.g, "tudo"), "dc")
        plano = sumario.priorizar(self.g, "Direito Constitucional", {})
        self.assertGreater(len(plano["modulos"]), 1)

    def test_assunto_inexistente_para_com_candidatos(self):
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer), self.assertRaises(SystemExit):
            sumario.resolver_assunto(self.g, "Direito Tributário")
        self.assertIn("Candidatos", buffer.getvalue())


class TestConferir(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        base = Path(self.dir.name)
        self.p_plano, self.p_grade = base / "plano.json", base / "grade.json"
        g = grafo_sintetico(
            [("raiz", None, "disciplina", 100, 100.0, 200, 3.0),
             ("a", "raiz", "topico", 100, 60.0, 120, 2.0),
             ("b", "raiz", "topico", 50, 40.0, 80, 1.0)],
            [("a", "b", "prerequisito")])
        self.plano = sumario.priorizar(g, "raiz", {})
        self.p_plano.write_text(json.dumps(self.plano, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.dir.cleanup()

    def grade_valida(self) -> dict:
        aulas, seq = [], 0
        for item in sorted(self.plano["itens"], key=lambda i: i["seq"]):
            for k, minutos in enumerate(item["minutos_por_aula"], 1):
                seq += 1
                aulas.append({"id": f"{item['num']}-{k}", "seq": seq, "item": item["num"],
                              "titulo": item["rotulo"], "minutos": minutos,
                              "importancia": item["importancia"]})
        return {"assunto": "raiz", "aulas": aulas}

    def rodar(self, grade: dict, sumario_md: str | None = None) -> int:
        self.p_grade.write_text(json.dumps(grade, ensure_ascii=False), encoding="utf-8")
        args = ["conferir", "--plano", str(self.p_plano), "--grade", str(self.p_grade)]
        if sumario_md is not None:
            caminho = Path(self.dir.name) / "sumario.md"
            caminho.write_text(sumario_md, encoding="utf-8")
            args += ["--sumario", str(caminho)]
        argv, sys.argv = sys.argv, ["sumario.py"] + args
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                sumario.main()
            return 0
        except SystemExit as e:
            return int(e.code or 0)
        finally:
            sys.argv = argv

    def test_grade_correta_passa(self):
        self.assertEqual(self.rodar(self.grade_valida()), 0)

    def test_item_esquecido_reprova(self):
        grade = self.grade_valida()
        grade["aulas"] = [a for a in grade["aulas"] if a["item"] != "1.2"]
        self.assertEqual(self.rodar(grade), 2)

    def test_item_omitido_com_justificativa_passa(self):
        grade = self.grade_valida()
        grade["aulas"] = [a for a in grade["aulas"] if a["item"] != "1.2"]
        grade["omitidos"] = [{"num": "1.2", "motivo": "coberto na revisão"}]
        self.assertEqual(self.rodar(grade), 0)

    def test_ordem_invertida_reprova(self):
        grade = self.grade_valida()
        total = len(grade["aulas"])
        for a in grade["aulas"]:                       # inverte a sequência inteira
            a["seq"] = total + 1 - a["seq"]
        self.assertEqual(self.rodar(grade), 2)

    def test_importancia_divergente_reprova(self):
        grade = self.grade_valida()
        grade["aulas"][0]["importancia"] = 1
        self.assertEqual(self.rodar(grade), 2)

    def test_minutos_divergentes_reprovam(self):
        grade = self.grade_valida()
        grade["aulas"][0]["minutos"] = 5
        self.assertEqual(self.rodar(grade), 2)

    def test_item_opcional_exige_omitidos_e_conferir_aceita_com_motivo(self):
        g = grafo_sintetico(
            [("raiz", None, "disciplina", 100, 100.0, 200, 3.0),
             ("a", "raiz", "topico", 100, 95.0, 196, 2.0),
             ("solto", "raiz", "topico", 5, 0.0, 0, 1.0)])
        g.nos["solto"].edital = 0.0
        self.plano = sumario.priorizar(g, "raiz", {})
        self.p_plano.write_text(json.dumps(self.plano, ensure_ascii=False), encoding="utf-8")
        solto = next(i for i in self.plano["itens"] if i["id"] == "solto")
        self.assertEqual(solto["formato"], "opcional")
        # a grade válida não cria aula para o opcional — mas omissão silenciosa reprova
        self.assertEqual(self.rodar(self.grade_valida()), 2)
        grade = self.grade_valida()
        grade["omitidos"] = [{"num": solto["num"], "motivo": solto["motivo_omissao"],
                              "formato": "opcional"}]
        self.assertEqual(self.rodar(grade), 0)

    def test_aula_curta_dividida_em_duas_reprova(self):
        g = grafo_sintetico(
            [("raiz", None, "disciplina", 100, 100.0, 200, 3.0),
             ("a", "raiz", "topico", 100, 95.0, 196, 2.0),
             ("vazio", "raiz", "topico", 5, 0.0, 0, 1.0)])
        self.plano = sumario.priorizar(g, "raiz", {})
        self.p_plano.write_text(json.dumps(self.plano, ensure_ascii=False), encoding="utf-8")
        vazio = next(i for i in self.plano["itens"] if i["id"] == "vazio")
        self.assertEqual(vazio["formato"], "curta")
        grade = self.grade_valida()
        self.assertEqual(self.rodar(grade), 0)
        unica = next(a for a in grade["aulas"] if a["item"] == vazio["num"])
        metade = unica["minutos"] // 2
        unica["minutos"] = metade
        grade["aulas"].append({**unica, "id": unica["id"] + "b",
                               "seq": len(grade["aulas"]) + 1,
                               "minutos": vazio["minutos"] - metade})
        self.assertEqual(self.rodar(grade), 2)

    def test_sumario_com_nota_inventada_reprova(self):
        self.assertEqual(self.rodar(self.grade_valida(), "Tópico brilhante — 11/10\n"), 2)
        self.assertEqual(self.rodar(self.grade_valida(), "# Sumário\n\n1.1 — 10/10\n"), 0)

    def test_sumario_com_percentual_inventado_reprova(self):
        self.assertEqual(self.rodar(self.grade_valida(), "cobre 42,7% das questões\n"), 2)

    def test_sumario_pode_dizer_quanto_ainda_falta(self):
        restante = self.plano["cobertura"]["curva"][0]["restante"] * 100
        texto = f"parar aqui deixa {restante:.1f}% da prova de fora\n".replace(".", ",")
        self.assertEqual(self.rodar(self.grade_valida(), texto), 0)

    def test_a_tabela_de_ancoras_nao_serve_de_alibi(self):
        # a seção "Como ler a nota" cita 1 a 10; ela é ignorada, senão validaria qualquer nota
        corpo = ("| 1.1 | Tópico | **9/10** |\n\n"
                 "## Como ler a nota\n\n| 9 | 90% do valor do topo |\n")
        self.assertEqual(self.rodar(self.grade_valida(), corpo), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
