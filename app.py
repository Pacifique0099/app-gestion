import streamlit as st
import sqlite3
import pandas as pd
import datetime
# --- SYSTÈME DE LICENCE ---
import hashlib
from supabase import create_client

# Remplacez par vos vraies infos copiées à l'étape 2
url = "https://cvouehtjccrwqwibbpty.supabase.co"
key = "sb_publishable_hO06P_FEf9CP8cighvS19Q_1tZ_S4hE"
supabase = create_client(url, key)

def verifier_licence_cloud(nom, cle):
    # Cette fonction va vérifier la clé sur Internet au lieu de votre PC
    result = supabase.table("licences").select("*").eq("nom", nom).eq("cle", cle).execute()
    return len(result.data) > 0

def check_license():
    """Vérifie l'activation locale et l'expiration sur Supabase"""
    with sqlite3.connect('boutique.db') as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS license_config (status TEXT, nom_boutique TEXT)")
        c.execute("SELECT status, nom_boutique FROM license_config")
        res = c.fetchone()
        
        if res and res[0] == "Active":
            # Si actif localement, on vérifie la date sur Supabase
            nom_btq = res[1]
            try:
                query = supabase.table("licences").select("expire_le").eq("nom", nom_btq).execute()
                if len(query.data) > 0:
                    return "Active", nom_btq, query.data[0]['expire_le']
            except:
                return "Active", nom_btq, None # En cas d'erreur réseau, on laisse passer
        return None

def activate_software(nom_saisi, cle_saisie):
    try:
        # On interroge Supabase pour voir si le couple Nom/Clé existe
        res = supabase.table("licences").select("*").eq("nom", nom_saisi).eq("cle", cle_saisie).execute()
        
        if len(res.data) > 0:
            # Si trouvé, on enregistre l'activation LOCALEMENT dans boutique.db
            with sqlite3.connect('boutique.db') as conn:
                c = conn.cursor()
                c.execute("DELETE FROM license_config")
                c.execute("INSERT INTO license_config (status, nom_boutique) VALUES ('Active', ?)", (nom_saisi,))
                conn.commit()
            return True
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
    return False

# --- DÉMARRAGE DU LOGICIEL ---

# 1. On vérifie la licence d'abord
licence_info = check_license()

if not licence_info or licence_info[0] != "Active":
    st.title("🛡️ Activation du Logiciel")
    st.markdown("---")
    st.warning("Ce logiciel n'est pas activé. Veuillez contacter le développeur pour obtenir une clé.")
    
    nom_boutique = st.text_input("Nom de votre Boutique (déclaré à l'achat)")
    cle_donnee = st.text_input("Clé d'activation", type="password")
    
    if st.button("Activer le logiciel"):
        if activate_software(nom_boutique, cle_donnee):
            st.success("✅ Activation réussie ! Relancement...")
            st.rerun()
        else:
            st.error("❌ Nom de boutique ou clé de licence invalide.")
    st.stop()# Arrête le code ici tant que ce n'est pas activé

# 2. Si activé, on affiche le nom de la boutique en haut
# --- VÉRIFICATION EXPIRATION & AFFICHAGE ---
licence_info = check_license()

if not licence_info:
    # ... (Gardez votre bloc d'activation st.title("🛡️ Activation") actuel ici) ...
    # Une fois activé, n'oubliez pas d'ajouter la ligne expire_le dans Supabase manuellement
    st.stop()

# Si on arrive ici, le logiciel est activé
status, nom_de_la_boutique, date_exp_str = licence_info

# --- SYSTÈME DE PAIEMENT / EXPIRATION ---
if date_exp_str:
    date_expiration = datetime.datetime.strptime(date_exp_str, '%Y-%m-%d').date()
    aujourdhui = datetime.date.today()
    jours_restants = (date_expiration - aujourdhui).days

    if jours_restants < 0:
        st.error(f"🚫 ACCÈS BLOQUÉ : L'abonnement de '{nom_de_la_boutique}' a expiré le {date_exp_str}.")
        st.info("Veuillez contacter Pacy MUHA au +257 79 799 794 pour le renouvellement.")
        st.stop() # Arrête tout le logiciel
    elif jours_restants <= 5:
        st.sidebar.warning(f"⚠️ Expire dans {jours_restants} jours")
# --- 1. INITIALISATION ---
def init_db():
    conn = sqlite3.connect('boutique.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS produits (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, prix_achat REAL, prix_vente REAL, quantite INTEGER, seuil_alerte INTEGER DEFAULT 5)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ventes (id INTEGER PRIMARY KEY AUTOINCREMENT, produit_id INTEGER, quantite_vendue INTEGER, prix_total REAL, type_paiement TEXT, nom_client TEXT, statut_dette TEXT DEFAULT 'Payé', date TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS comptes_clients (id INTEGER PRIMARY KEY AUTOINCREMENT, nom_client TEXT UNIQUE, solde REAL DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS depenses (id INTEGER PRIMARY KEY AUTOINCREMENT, motif TEXT, montant REAL, date TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS utilisateurs (id INTEGER PRIMARY KEY AUTOINCREMENT, identifiant TEXT UNIQUE, mot_de_passe TEXT, role TEXT)''')
    # Table pour l'historique des arrivages
    c.execute('''CREATE TABLE IF NOT EXISTS arrivages (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, quantite REAL, date TEXT DEFAULT CURRENT_TIMESTAMP)''')
    
    # Table pour suivre les connexions
    c.execute('''CREATE TABLE IF NOT EXISTS presence (id INTEGER PRIMARY KEY AUTOINCREMENT, utilisateur TEXT, date_connexion TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM utilisateurs")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO utilisateurs (identifiant, mot_de_passe, role) VALUES (?,?,?)", ('admin', 'admin', 'Patron'))
    conn.commit()
    conn.close()

init_db()

# Vérification de la licence avant tout
if not licence_info or licence_info[0] != "Active":
    st.title("🛡️ Activation du Logiciel")
    st.warning("Ce logiciel n'est pas activé. Veuillez contacter Pacy MHA.")
    
    # On crée les deux champs de saisie
    nom_boutique = st.text_input("Nom de votre Boutique")
    cle_donnee = st.text_input("Saisissez votre clé de licence", type="password")
    
    if st.button("Activer le logiciel"):
        # ICI : On envoie bien les DEUX variables à la fonction
        if activate_software(nom_boutique, cle_donnee):
            st.success("✅ Activation réussie !")
            st.rerun()
        else:
            st.error("❌ Nom ou Clé invalide.")
    st.stop()
# --- 2. CONNEXION ---
if "auth" not in st.session_state:
    st.session_state.auth, st.session_state.role, st.session_state.user = False, None, None

# --- 2. CONNEXION (Modifié) ---
if not st.session_state.auth:
    st.title("🔐 Bienvenue")
    with st.form("login"):
        u = st.text_input("Identifiant").lower() # Ajout de .lower() ici
        p = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Se connecter"):
            conn = sqlite3.connect('boutique.db')
            c = conn.cursor()
            # On cherche l'utilisateur
            c.execute("SELECT role FROM utilisateurs WHERE identifiant=? AND mot_de_passe=?", (u, p))
            res = c.fetchone()
            if res:
                st.session_state.auth, st.session_state.role, st.session_state.user = True, res[0], u
                # On enregistre la présence (comme suggéré avant)
                c.execute("INSERT INTO presence (utilisateur, date_connexion) VALUES (?, CURRENT_TIMESTAMP)", (u,))
                conn.commit()
                st.rerun()
            else: 
                st.error("Identifiants incorrects")
            conn.close()
    st.stop()

conn = sqlite3.connect('boutique.db')

# --- SIDEBAR & MENU ---
st.sidebar.title(f"👤 {st.session_state.user}")
st.sidebar.info(f"Rôle : {st.session_state.role}")

# Alertes stock (Bouton dynamique)
low_stock_query = pd.read_sql_query("SELECT nom, quantite FROM produits WHERE quantite <= seuil_alerte", conn)
alert_label = f"⚠️ Alertes Stock ({len(low_stock_query)})" if not low_stock_query.empty else "✅ Stock OK"

options = ["🛒 Caisse", "📦 Stock", "📜 Historique Arrivages", alert_label, "💸 Finances & Dépenses"]
if st.session_state.role == "Patron": 
    options += ["📊 Tableau de Bord", "👥 Employés en Ligne", "⚙️ Paramètres","☎️ Aide & Support"]

menu = st.sidebar.radio("Menu Principal", options)

if st.sidebar.button("🚪 Se déconnecter"):
    st.session_state.auth = False
    st.rerun()

# --- SECTION : CAISSE ---
# --- SECTION : CAISSE ---
if menu == "🛒 Caisse":
    st.header("🛒 Caisse")
    if 'panier' not in st.session_state: st.session_state.panier = []
    
    with sqlite3.connect('boutique.db') as conn:
        p_df = pd.read_sql_query("SELECT * FROM produits WHERE quantite > 0", conn)
        
        if not p_df.empty:
            st.subheader("🛒 Ajouter des articles")
            c1, c2, c3 = st.columns([2, 1, 1])
            
            choix = c1.selectbox("Produit", p_df['nom'].tolist())
            pi = p_df[p_df['nom'] == choix].iloc[0]
            
            qte = c2.number_input("Quantité", min_value=0.01, value=0.01)
            # Case de prix modifiable (propose le prix de vente par défaut)
            prix_vente_final = c3.number_input("Prix de Vente (FG)", min_value=0.0, value=float(pi['prix_vente']))
            
            if st.button("➕ Ajouter au Panier"):
                st.session_state.panier.append({
                    "id": int(pi['id']), 
                    "nom": choix, 
                    "qte": int(qte), 
                    "prix": prix_vente_final, 
                    "total": qte * prix_vente_final
                })
                st.rerun()

        if st.session_state.panier:
            st.divider()
            st.subheader("📋 Panier actuel")
            df_p = pd.DataFrame(st.session_state.panier)
            st.table(df_p[['nom', 'qte', 'prix', 'total']])
            
            total_panier = df_p['total'].sum()
            st.write(f"### 💰 Total à payer : {total_panier:,.0f} FG")
            
            # --- BLOC DE VALIDATION ---
            st.subheader("💳 Finaliser la vente")
            m = st.radio("Mode de paiement", ["Cash", "Dette", "Avance"], horizontal=True)
            
            nc = ""
            valider_possible = True
            
            if m == "Avance":
                avances_df = pd.read_sql_query("SELECT nom_client, solde FROM comptes_clients WHERE solde > 0", conn)
                if avances_df.empty:
                    st.error("⚠️ Aucun client n'a d'avance enregistrée.")
                    valider_possible = False
                else:
                    nc = st.selectbox("Sélectionner le client", avances_df['nom_client'].tolist())
                    solde_client = avances_df[avances_df['nom_client'] == nc]['solde'].values[0]
                    st.info(f"Solde disponible : {solde_client:,.0f} FG")
                    
                    # Message explicatif si l'avance ne couvre pas tout
                    if solde_client < total_panier:
                        dette_reste = total_panier - solde_client
                        st.warning(f"⚠️ L'avance couvre {solde_client:,.0f} FG. Le reste ({dette_reste:,.0f} FG) sera enregistré en DETTE.")
            else:
                nc = st.text_input("Nom du Client / N° Ticket")

            if st.button("✅ VALIDER LA VENTE") and valider_possible:
                if nc == "" and m != "Avance":
                    st.error("Veuillez saisir un nom de client.")
                else:
                    with sqlite3.connect('boutique.db') as conn_val:
                        cur = conn_val.cursor()
                        
                        # --- GESTION SPÉCIALE DU PAIEMENT PAR AVANCE ---
                        if m == "Avance":
                            solde_client = pd.read_sql_query("SELECT solde FROM comptes_clients WHERE nom_client = ?", conn_val, params=(nc,)).iloc[0,0]
                            
                            if solde_client >= total_panier:
                                # L'avance suffit à tout payer
                                cur.execute("UPDATE comptes_clients SET solde = solde - ? WHERE nom_client = ?", (total_panier, nc))
                                type_p, statut_d = "Avance", "Payé"
                                total_vente_enregistre = total_panier
                            else:
                                # L'avance est insuffisante : on vide le solde client et le reste va en Dette
                                reste_en_dette = total_panier - solde_client
                                cur.execute("UPDATE comptes_clients SET solde = 0 WHERE nom_client = ?", (nc,))
                                
                                # 1. On enregistre la partie payée par avance
                                if solde_client > 0:
                                    for i in st.session_state.panier:
                                        cur.execute("""INSERT INTO ventes (produit_id, quantite_vendue, prix_total, type_paiement, nom_client, statut_dette) 
                                                        VALUES (?,?,?,?,?,?)""",
                                                    (i['id'], i['qte'], solde_client, "Avance", nc, "Payé"))
                                        break # Enregistre l'avance globale sur le premier article pour le total
                                
                                # 2. La dette enregistrée pour la partie manquante
                                type_p, statut_d = "Dette", "Non Payé"
                                total_vente_enregistre = reste_en_dette
                        else:
                            type_p = m
                            statut_d = "Payé" if m != "Dette" else "Non Payé"
                            total_vente_enregistre = total_panier

                        # --- ENREGISTREMENT DE LA VENTE ET DÉDUCTION DU STOCK ---
                        if m != "Avance" or (m == "Avance" and solde_client >= total_panier):
                            for i in st.session_state.panier:
                                cur.execute("UPDATE produits SET quantite = quantite - ? WHERE id = ?", (i['qte'], i['id']))
                                cur.execute("""INSERT INTO ventes (produit_id, quantite_vendue, prix_total, type_paiement, nom_client, statut_dette) 
                                                VALUES (?,?,?,?,?,?)""",
                                            (i['id'], i['qte'], i['total'], type_p, nc, statut_d))
                        elif m == "Avance" and solde_client < total_panier:
                            # Déduction des stocks dans le cas mixte (Avance + Dette)
                            for i in st.session_state.panier:
                                cur.execute("UPDATE produits SET quantite = quantite - ? WHERE id = ?", (i['qte'], i['id']))
                            # Enregistrement de la dette résiduelle
                            premiere_item = st.session_state.panier[0]
                            cur.execute("""INSERT INTO ventes (produit_id, quantite_vendue, prix_total, type_paiement, nom_client, statut_dette) 
                                            VALUES (?,?,?,?,?,?)""",
                                        (premiere_item['id'], premiere_item['qte'], reste_en_dette, "Dette", nc, "Non Payé"))

                        conn_val.commit()
                        st.session_state.panier = [] # Vider le panier
                        st.success("🎉 Vente enregistrée avec succès !")
                        st.rerun()
                        
        if st.button("🗑️ Vider le panier"):
            st.session_state.panier = []
            st.rerun()

# --- SECTION : STOCK ---
elif menu == "📦 Stock":
    st.header("📦 Gestion des Stocks")
    tab_inventaire, tab_nouveau = st.tabs(["📋 Inventaire & Modifications", "🆕 Nouvel Arrivage"])
    
    with tab_inventaire:
        df_stock = pd.read_sql_query("SELECT * FROM produits", conn)
        cols = st.columns([3, 2, 2, 2, 1])
        cols[0].write("**Nom**")
        cols[1].write("**Prix Achat**")
        cols[2].write("**Prix Vente**")
        cols[3].write("**Quantité**")
        cols[4].write("**Action**")
        st.divider()

        for index, row in df_stock.iterrows():
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
            c1.write(row['nom'])
            c2.write(f"{row['prix_achat']}" if st.session_state.role == "Patron" else "---")
            c3.write(f"{row['prix_vente']}")
            c4.write(f"{row['quantite']}")
            if st.session_state.role == "Patron":
                if c5.button("📝", key=f"edit_{row['id']}"):
                    st.session_state.editing_prod = row['id']
                    st.rerun()
            else: c5.write("🔒")

        if "editing_prod" in st.session_state:
            st.divider()
            st.subheader("🛠️ Modifier le produit")
            prod_to_edit = df_stock[df_stock['id'] == st.session_state.editing_prod].iloc[0]
            with st.form("form_edit"):
                new_nom = st.text_input("Nom", value=prod_to_edit['nom'])
                new_pa = st.number_input("Prix Achat", value=float(prod_to_edit['prix_achat']))
                new_pv = st.number_input("Prix Vente", value=float(prod_to_edit['prix_vente']))
                new_qte = st.number_input("Quantité", value=int(prod_to_edit['quantite']))
                if st.form_submit_button("✅ Enregistrer"):
                    cur = conn.cursor()
                    cur.execute("UPDATE produits SET nom=?, prix_achat=?, prix_vente=?, quantite=? WHERE id=?", (new_nom.upper(), new_pa, new_pv, new_qte, st.session_state.editing_prod))
                    conn.commit(); del st.session_state.editing_prod; st.success("Mis à jour !"); st.rerun()

    with tab_nouveau:
        st.subheader("Entrée de marchandise")
        # VIDAGE AUTOMATIQUE : On n'utilise pas d'index de session_state ici pour que le formulaire se reset seul au rerun
        with st.form("arrivage", clear_on_submit=True):
            n = st.text_input("Nom de l'article").upper()
            q = st.number_input("Quantité reçue", min_value=1)
            pa = st.number_input("Prix d'Achat (Unitaire)", value=0.0) if st.session_state.role == "Patron" else 0.0
            pv = st.number_input("Prix de Vente (Unitaire)", value=0.0) if st.session_state.role == "Patron" else 0.0
            
            if st.form_submit_button("💾 Enregistrer l'Arrivage"):
                c = conn.cursor()
                # Log de l'arrivage
                c.execute("INSERT INTO arrivages (nom, quantite) VALUES (?,?)", (n, q))
                # Update stock
                c.execute("SELECT id FROM produits WHERE nom=?", (n,))
                ex = c.fetchone()
                if ex:
                    if st.session_state.role == "Patron":
                        c.execute("UPDATE produits SET quantite=quantite+?, prix_achat=?, prix_vente=? WHERE id=?", (q, pa, pv, ex[0]))
                    else:
                        c.execute("UPDATE produits SET quantite=quantite+? WHERE id=?", (q, ex[0]))
                else:
                    c.execute("INSERT INTO produits (nom, prix_achat, prix_vente, quantite) VALUES (?,?,?,?)", (n, pa, pv, q))
                conn.commit(); st.success(f"✅ Réussi : {q} {n} ajouté(s) !"); st.rerun()

# --- SECTION : HISTORIQUE ARRIVAGES ---
elif menu == "📜 Historique Arrivages":
    st.header("📜 Historique des Nouveaux Arrivages")
    df_arr = pd.read_sql_query("SELECT date, nom, quantite FROM arrivages ORDER BY id DESC", conn)
    st.dataframe(df_arr, use_container_width=True)

# --- SECTION : ALERTES STOCK ---
elif menu == alert_label:
    st.header("⚠️ Produits en rupture ou stock faible")
    if not low_stock_query.empty:
        st.error(f"Il y a {len(low_stock_query)} produit(s) à racheter immédiatement.")
        st.table(low_stock_query)
    else:
        st.success("Tout est en stock !")

# --- SECTION : FINANCES & DÉPENSES (OUVERT À TOUS) ---
elif menu == "💸 Finances & Dépenses":
    st.header("💸 Suivi Financier")
    t1, t2, t3 = st.tabs(["🤝 Dettes Clients", "🏦 Avances", "💰 Dépenses"])
    
    with t1:
        d_df = pd.read_sql_query("SELECT v.id, v.nom_client, p.nom as produit, v.prix_total FROM ventes v JOIN produits p ON v.produit_id = p.id WHERE v.statut_dette = 'Non Payé'", conn)
        if not d_df.empty:
            for cl in d_df['nom_client'].unique():
                with st.expander(f"👤 {cl} | Total Dû : {d_df[d_df['nom_client']==cl]['prix_total'].sum():,.0f} FG"):
                    st.table(d_df[d_df['nom_client']==cl][['produit', 'prix_total']])
            
            sel_cl = st.selectbox("Sélectionner Client pour Paiement", d_df['nom_client'].unique())
            art_cl = st.selectbox("Article concerné", d_df[d_df['nom_client']==sel_cl]['produit'].tolist())
            r = d_df[(d_df['nom_client']==sel_cl) & (d_df['produit']==art_cl)].iloc[0]
            vers = st.number_input("Somme versée", max_value=float(r['prix_total']))
            if st.button("Valider Paiement Dette"):
                c = conn.cursor()
                nv = r['prix_total'] - vers
                c.execute("UPDATE ventes SET prix_total=?, statut_dette=? WHERE id=?", (nv, 'Payé' if nv <= 0 else 'Non Payé', int(r['id'])))
                conn.commit(); st.success("Paiement enregistré !"); st.rerun()
        else: st.info("Aucune dette en cours.")

    with t2:
        with st.form("avance"):
            na, ma = st.text_input("Nom du Client"), st.number_input("Montant de l'avance", min_value=0.0)
            if st.form_submit_button("Ajouter Avance"):
                c = conn.cursor(); c.execute("INSERT INTO comptes_clients (nom_client, solde) VALUES (?,?) ON CONFLICT(nom_client) DO UPDATE SET solde=solde+?", (na, ma, ma))
                conn.commit(); st.success("Avance ajoutée !"); st.rerun()
        st.dataframe(pd.read_sql_query("SELECT nom_client, solde FROM comptes_clients WHERE solde > 0", conn))

    with t3:
        with st.form("depense"):
            mo, mt = st.text_input("Motif"), st.number_input("Montant", min_value=0.0)
            if st.form_submit_button("Enregistrer Dépense"):
                c = conn.cursor(); c.execute("INSERT INTO depenses (motif, montant) VALUES (?,?)", (mo, mt)); conn.commit(); st.success("Dépense notée !"); st.rerun()
        st.table(pd.read_sql_query("SELECT date, motif, montant FROM depenses ORDER BY id DESC", conn))

# --- SECTION : TABLEAU DE BORD (PATRON SEULEMENT) ---
elif menu == "📊 Tableau de Bord":
    st.header("📊 Performance & Statistiques")
    
    # KPIs
    q_stats = "SELECT SUM(v.prix_total) as CA, SUM(v.prix_total - (p.prix_achat * v.quantite_vendue)) as Benef FROM ventes v JOIN produits p ON v.produit_id = p.id"
    res = pd.read_sql_query(q_stats, conn)
    dep_total = pd.read_sql_query("SELECT SUM(montant) FROM depenses", conn).iloc[0,0] or 0
    
    c1, c2, c3 = st.columns(3)
    ca = res['CA'].sum() or 0
    benef_b = res['Benef'].sum() or 0
    c1.metric("Chiffre d'Affaires", f"{ca:,.0f} FG")
    c2.metric("Bénéfice Brut", f"{benef_b:,.0f} FG")
    c3.metric("Bénéfice Net (Moins Dépenses)", f"{(benef_b - dep_total):,.0f} FG")
    
    # DIAGRAMME DES VENTES
    st.subheader("📈 Évolution des Ventes")
    df_chart = pd.read_sql_query("SELECT date, SUM(prix_total) as total FROM ventes GROUP BY date", conn)
    if not df_chart.empty:
        df_chart['date'] = pd.to_datetime(df_chart['date'])
        st.line_chart(df_chart.set_index('date'))

        # --- BOUTON D'EXPORTATION ---
    st.divider()
    st.subheader("📥 Exporter les données")
    
    # On prépare les données des ventes pour l'export
    df_export = pd.read_sql_query("""
        SELECT v.date, v.nom_client, p.nom as produit, 
               v.quantite_vendue, v.prix_total, v.type_paiement, v.statut_dette 
        FROM ventes v JOIN produits p ON v.produit_id = p.id
    """, conn)

    # Création du bouton de téléchargement (Format CSV, lisible par Excel)
    csv = df_export.to_csv(index=False).encode('utf-8-sig') # utf-8-sig pour que les accents s'affichent bien dans Excel
    
    st.download_button(
        label="📥 Télécharger l'Historique des Ventes (Excel/CSV)",
        data=csv,
        file_name=f'ventes_boutique_{datetime.date.today()}.csv',
        mime='text/csv',
    )
    
    # HISTORIQUE COMPLET
    st.subheader("📜 Historique de chaque vente")
    hist_q = """SELECT v.date, v.nom_client, p.nom as produit, v.quantite_vendue as qte, v.prix_total as total, v.type_paiement 
                FROM ventes v JOIN produits p ON v.produit_id = p.id ORDER BY v.id DESC"""
    st.dataframe(pd.read_sql_query(hist_q, conn), use_container_width=True)

# --- SECTION : EMPLOYES EN LIGNE (NOUVEAU) ---
elif menu == "👥 Employés en Ligne" and st.session_state.role == "Patron":
    st.header("👥 Présence des Employés")
    df_presence = pd.read_sql_query("SELECT utilisateur as 'Employé', MAX(date_connexion) as 'Dernière Connexion' FROM presence GROUP BY utilisateur ORDER BY date_connexion DESC", conn)
    st.table(df_presence)

# --- SECTION : PARAMÈTRES ---
elif menu == "⚙️ Paramètres":
    st.header("⚙️ Paramètres")
    t_compte, t_equipe = st.tabs(["👤 Mon Compte", "👥 Gestion Équipe"])
    with t_compte:
        un = st.text_input("Nouveau Nom", value=st.session_state.user)
        up = st.text_input("Nouveau Mot de passe", type="password")
        if st.button("Sauvegarder"):
            c = conn.cursor()
            c.execute("UPDATE utilisateurs SET identifiant=?, mot_de_passe=? WHERE identifiant=?", (un, up, st.session_state.user))
            conn.commit(); st.session_state.user = un; st.success("Mis à jour !"); st.rerun()
    with t_equipe:
        st.subheader("Ajouter un nouvel employé")
        with st.form("creer_employe", clear_on_submit=True):
            nu = st.text_input("Nom de l'Employé (Identifiant)")
            np = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("➕ Créer l'accès"):
                if nu and np:
                    c = conn.cursor()
                    try:
                        # On force l'identifiant en minuscules pour éviter les erreurs
                        c.execute("INSERT INTO utilisateurs (identifiant, mot_de_passe, role) VALUES (?,?,'Employé')", 
                                 (nu.lower(), np))
                        conn.commit()
                        st.success(f"Compte créé pour {nu} !")
                        st.rerun() # Très important pour mettre à jour la liste
                    except sqlite3.IntegrityError:
                        st.error("Cet identifiant existe déjà.")
                else:
                    st.warning("Veuillez remplir tous les champs.")
        
        st.divider()
        st.write("### Liste du personnel")
        st.dataframe(pd.read_sql_query("SELECT identifiant, role FROM utilisateurs", conn), use_container_width=True)

elif menu == "☎️ Aide & Support":
    st.header("☎️ Assistance Technique")
    st.write("Besoin d'aide ou d'une nouvelle fonctionnalité ? Contactez votre développeur.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        ### 👨‍💻 Développeur : Pacy MUHA
        - **Téléphone :** +257 79 799 794
        - **Email :** mbonimpapacy1@gmail.com
        - **Services :** Mise à jour, Maintenance, Formation.
        """)
        
    with col2:
        # On récupère les infos d'expiration en temps réel sur Supabase
        try:
            res = supabase.table("licences").select("expire_le").eq("nom", nom_de_la_boutique).execute()
            if res.data:
                date_exp_str = res.data[0]['expire_le']
                date_expiration = datetime.datetime.strptime(date_exp_str, '%Y-%m-%d').date()
                aujourdhui = datetime.date.today()
                jours_restants = (date_expiration - aujourdhui).days
                
                status_color = "✅" if jours_restants > 5 else "⚠️"
                info_abo = f"{status_color} Expire le : {date_exp_str} ({jours_restants} jours restants)"
            else:
                info_abo = "ℹ️ Statut non défini"
        except:
            info_abo = "❌ Erreur de connexion au serveur de licence"

        st.success(f"""
        ### 🛡️ État du Logiciel
        - **Version :** 1.0.0 (Pro)
        - **Boutique :** {nom_de_la_boutique}
        - **Abonnement :** {info_abo}
        - **Base de données :** Connectée
        """)

    st.divider()
    st.subheader("📩 Envoyer un message rapide")
    with st.form("support_form"):
        sujet = st.selectbox("Sujet", ["Problème technique", "Demande de formation", "Ajout de fonctionnalité", "Autre"])
        message = st.text_area("Expliquez votre besoin ici...")
        if st.form_submit_button("Envoyer la demande"):
            # Ici, comme c'est local, on simule l'envoi
            st.success("Votre demande a été enregistrée. Pacy MHA vous contactera sous peu.")

   










