# -*- encoding: utf-8 -*-

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import decimal_precision as dp
import time
import netsvc
import pooler, tools
import math
from tools.translate import _
import base64

from osv import fields, osv

def arrot(cr,uid,valore,decimali):
    #import pdb;pdb.set_trace()
    return round(valore,decimali(cr)[1])


class FiscalDocHeader(osv.osv):
    _inherit = 'fiscaldoc.header'

    _columns={
                'flag_exp_adhoc':fields.boolean("Esportato verso Ad-Hoc"),


              }
        
FiscalDocHeader()


class GenFileadprinot_Doc(osv.osv_memory):
    _name = 'gen_adprinot_doc'
    _description = 'Genera file di prima nota dai doc di vendita  '

    def _get_conti_iva(self,cr, uid, context=None):
       conto_iva  =  self.pool.get('account.account').search(cr,uid,[('code','=','0603004')])[0]       
       return conto_iva

    def _get_conti_conai(self,cr, uid, context=None):
       
       conto_conai  =  self.pool.get('account.account').search(cr,uid,[('code','=','0804003')])[0]
       return conto_conai 
   
    def _get_conti_traspo(self,cr, uid, context=None):
       
       conto_traspo  =  self.pool.get('account.account').search(cr,uid,[('code','=','1030001')])[0]
       return conto_traspo 
  
    
    _columns = {
                    'dadatadoc': fields.date('Da Data Documento', required=True ),
                    'adatadoc': fields.date('A Data Documento', required=True),
                    'contoiva_id':fields.many2one('account.account', "Conto Iva", required=True  ),                    
                    'contoconai_id':fields.many2one('account.account', "Cotropartita Conai", required=True ),
                    'contotrasp_id':fields.many2one('account.account', "Cotropartita Spese Trasporto", required=True ),
                    }
    _defaults = {
                 'contoiva_id':_get_conti_iva,
                 'contoconai_id':_get_conti_conai,
                 'contotrasp_id':_get_conti_traspo,
                 }
    
  
    def genera_adprinot(self, cr, uid, ids, context=None):    
        par= self.browse(cr,uid,ids)[0]
        doc_head_obj = self.pool.get('fiscaldoc.header')
        tmpfileadprinot_obj = self.pool.get('tmpfileadprinot')
        tmpfileadclifor_obj = self.pool.get('tmpfileadclifor')
        ok = tmpfileadprinot_obj.pulisce(cr,uid,ids)
        ok = tmpfileadclifor_obj.pulisce(cr,uid,ids)
        numero_reg = 0
        
        if par.dadatadoc and par.adatadoc and par.adatadoc>=par.dadatadoc:
            cerca =[('data_documento',">=",par.dadatadoc),('data_documento',"<=",par.adatadoc),('flag_exp_adhoc','=',False)]
            docs_ids = doc_head_obj.search(cr,uid,cerca,order='data_documento,name')
            if docs_ids:
                tot_errori= []
                for doc in doc_head_obj.browse(cr,uid,docs_ids):
                    # cicla sui documenti trovati
                    if doc.tipo_doc.tipo_documento in ['FA','FD','FI','ND','NC'] and doc.tipo_doc.flag_contabile== True:
                        # DOCUMENTO IDONEO ALLA ESPORTAZIONE
                        numero_reg += 1
                        errori = self.scrive_registrazione(cr, uid,ids, doc, numero_reg)
                        tot_errori += errori                        
                        ok = doc_head_obj.write(cr,uid,[doc.id],{'flag_exp_adhoc':True})
                if numero_reg > 0:
                    file = """"""
                    for e in tot_errori:
                                file += e +  "\r\n"
                                file = """"""
                                file_name = '/home/openerp/primanota/'+'errori.txt'
                                fp = open(file_name, 'wb+');
                                fp.write(file);
                                fp.close();
                    
                    ok = tmpfileadprinot_obj.scrive_file(cr,uid,ids)
                    ok = tmpfileadclifor_obj.scrive_file(cr,uid,ids)
                else:
                    raise osv.except_osv(_('ERRORE !'),_('Non sono presenti documenti per questa selezione'))
                            
            else:                
                raise osv.except_osv(_('ERRORE !'),_('Non sono presenti documenti per questa selezione'))
        else:
               raise osv.except_osv(_('ERRORE !'),_('Devi Selezionare Meglio le Date Documento'))
        return {'type': 'ir.actions.act_window_close'}
           
    def scrive_registrazione(self,cr,uid,ids,doc,numero_reg):
        errori=[]
        par= self.browse(cr,uid,ids)[0]
        tmpfileadprinot_obj = self.pool.get('tmpfileadprinot')
        tmpfileadclifor_obj = self.pool.get('tmpfileadclifor')
        partner_obj = self.pool.get('res.partner').browse(cr, uid, doc.partner_id.id)
        numero_riga = 0
        riga = {}
        # scrive il primo record, quello che riguarda il cliente
        numero_riga +=1
        
        datadoc = doc.data_documento.replace('-','')
        #datasca = doc.data_scadenza
        riga['numriga']= numero_riga
        riga['numreg'] = numero_reg
        riga['datreg']= datadoc
        riga['causale']= doc.tipo_doc.name
        riga['dtcompiva']= datadoc
        riga['numdoc'] = doc.numdoc
        riga['alfadoc'] = " "*2
        riga['dtdoc'] = datadoc
        riga['numprot']= 0
        riga['note'] = "Documento "+doc.name
        conto_partner = self.pool.get('account.account').browse(cr,uid,partner_obj.property_account_receivable.id).code
        riga['sottoconto'] = conto_partner
        riga['testcf'] = 'C'
        riga['codclifor'] = partner_obj.ref
        if partner_obj.vat:
            riga['piva']= partner_obj.vat[2:]
        else:
            riga['piva']=''
        riga['codiceiva']=''
        riga['imponibile']='0'*15
        if doc.tipo_doc.tipo_documento=='NC':
            # nota credito cliente in avere
            riga['impoavere'] = self.formatta_num(cr, uid, doc.totale_documento,15)
            riga['impodare'] = '0'*15
            
        else:
            # tipo fattura cliente in dare
            
            riga['impodare'] = self.formatta_num(cr, uid, doc.totale_documento,15)
            riga['impoavere'] = '0'*15
        riga['valuta']='6'
        riga['cambio']= "1".rjust(12,"0")
        riga['diffiva'] = "0"*4
        riga['codpag'] = doc.pagamento_id.name[0:4]
        riga['flagintra']=""
        riga['dtdiversa']=datadoc
        riga['cotropatita'] =""
        riga['cliforcontrop']=""
        riga['impregval'] = "0"*15
        # import pdb;pdb.set_trace()
        id_rec = tmpfileadprinot_obj.create(cr,uid,riga)
        # SCIRVE LE RIGHE IVA
        for riga_iva in doc.righe_totali_iva:
            numero_riga +=1
            riga = {}
            riga['numriga']= numero_riga
            riga['numreg'] = numero_reg
            riga['datreg']= datadoc
            riga['causale']= doc.tipo_doc.name
            riga['dtcompiva']= datadoc
            riga['numdoc'] = doc.numdoc
            if doc.tipo_doc.tipo_documento=='NC':
                riga['alfadoc'] ='NC'
            else:
                riga['alfadoc'] = " "*2
            riga['dtdoc'] = datadoc
            riga['numprot']= 0
            riga['note'] = "Documento "+doc.name
            riga['sottoconto'] =  par.contoiva_id.code
            riga['testcf'] = ''
            riga['codclifor'] = ''
            riga['piva']= ''
           
            riga['codiceiva']=riga_iva.codice_iva.description
            riga['imponibile']=self.formatta_num(cr, uid, riga_iva.imponibile,15)
            if doc.tipo_doc.tipo_documento=='NC':
            # nota credito cliente in avere
             riga['impodare'] = self.formatta_num(cr, uid, riga_iva.imposta,15)
             riga['impoavere'] = '0'*15           
            else:
            # tipo fattura cliente in dare
               riga['impoavere'] = self.formatta_num(cr, uid,riga_iva.imposta,15)
               riga['impodare'] = '0'*15
            riga['valuta']='6'
            riga['cambio']= "1".rjust(12,"0")
            riga['diffiva'] = "0"*4

            riga['codpag'] = doc.pagamento_id.name[0:4]

            riga['flagintra']=""
            riga['dtdiversa']=datadoc
            riga['cotropatita'] =""
            riga['cliforcontrop']=""
            riga['impregval'] = "0"*15
            
            id_rec = tmpfileadprinot_obj.create(cr,uid,riga)
        righe_contr = {}
        lista_contr =[]
        if doc.spese_trasporto:
              righe_contr[par.contotrasp_id.id] = righe_contr.get(par.contotrasp_id.id,0)+ doc.spese_trasporto
        
        for riga_art in doc.righe_articoli:
          #import pdb;pdb.set_trace()
          if riga_art.totale_riga<>0:     
            if doc.sconto_partner or doc.sconto_pagamento:
                    netto = riga_art.totale_riga
                    netto = arrot(cr,uid,netto,dp.get_precision('Account'))
                    if doc.sconto_partner:
                        netto = netto-(netto*doc.sconto_partner/100)
                        #netto = arrot(cr,uid,netto,dp.get_precision('Account'))
                    if doc.sconto_pagamento:
                        netto = netto-(netto*doc.sconto_pagamento/100)
                        #netto = arrot(cr,uid,netto,dp.get_precision('Account'))
            else:
                    netto = riga_art.totale_riga
                    netto = arrot(cr,uid,netto,dp.get_precision('Account'))
                    

                     
            if riga_art.contropartita:
                # c'è la contropartita
                righe_contr[riga_art.contropartita.id] = righe_contr.get(riga_art.contropartita.id,0)+ netto
            else:
                # non c'è la cerca prima sull'articolo ancora è stato inserito dopo e poi sulla categoria
                if riga_art.product_id.property_account_income: # Trovato Sulla Articolo
                    righe_contr[riga_art.product_id.property_account_income.id] = righe_contr.get(riga_art.product_id.property_account_income.id,0)+ netto                    
                else:
                    if riga_art.product_id.categ_id.property_account_income_categ:
                        righe_contr[riga_art.product_id.categ_id.property_account_income_categ.id] = righe_contr.get(riga_art.product_id.categ_id.property_account_income_categ.id,0)+ netto
                        #trovato sulla categoria
                    else:
                        errori.append("Contropartita non trovata su articolo "+riga_art.product_id.default_code+ " Documento "+doc.name)
                        print "Contropartita non trovata su articolo "+riga_art.product_id.default_code+ " Documento "+doc.name
          if riga_art.totale_conai:
                # c'è conai
                righe_contr[par.contoconai_id.id] = righe_contr.get(par.contoconai_id.id,0)+  arrot(cr,uid,riga_art.totale_conai,dp.get_precision('Account'))
        #import pdb;pdb.set_trace()
        for riga_contr in righe_contr:
            numero_riga +=1
            riga = {}
            controp=riga_contr
            contro = self.pool.get('account.account').browse(cr,uid,controp)
            riga['numriga']= numero_riga
            riga['numreg'] = numero_reg
            riga['datreg']= datadoc
            riga['causale']= doc.tipo_doc.name
            riga['dtcompiva']= datadoc
            riga['numdoc'] = doc.numdoc
            if doc.tipo_doc.tipo_documento=='NC':
                riga['alfadoc'] ='NC'
            else:
                riga['alfadoc'] = " "*2
            riga['dtdoc'] = datadoc
            riga['numprot']= 0
            riga['note'] = "Documento "+doc.name
            riga['sottoconto'] =  contro.code
            riga['testcf'] = ''
            riga['codclifor'] = ''
            riga['piva']= ''
            riga['codiceiva']=''
            riga['imponibile']='0'*15
            #import pdb;pdb.set_trace()
            if doc.tipo_doc.tipo_documento=='NC':
            # nota credito cliente in avere
             riga['impodare'] = self.formatta_num(cr, uid, righe_contr.get(controp,0),15)
             riga['impoavere'] = '0'*15           
            else:
            # tipo fattura cliente in dare
               riga['impoavere'] = self.formatta_num(cr, uid,righe_contr.get(controp,0),15)
               riga['impodare'] = '0'*15
            riga['valuta']='6'
            riga['cambio']= "1".rjust(12,"0")
            riga['diffiva'] = "0"*4
            riga['codpag'] = doc.pagamento_id.name[0:4]
            riga['flagintra']=""
            riga['dtdiversa']=datadoc
            riga['cotropatita'] =""
            riga['cliforcontrop']=""
            riga['impregval'] = "0"*15
            #import pdb;pdb.set_trace()
            id_rec = tmpfileadprinot_obj.create(cr,uid,riga)
        partner_obj = self.pool.get('res.partner').browse(cr, uid, doc.partner_id.id)
        
        if partner_obj and ('P/'in partner_obj.ref or 'L'in partner_obj.ref):
            # è movimentato il partner
            id_tmcli = tmpfileadclifor_obj.search(cr,uid,[('partner_id','=',partner_obj.id)])
            addr_id = self.pool.get('res.partner').address_get(cr, uid, [partner_obj.id], ['default'])
            addr = self.pool.get('res.partner.address').browse(cr,uid,addr_id['default'])
            if not id_tmcli:
                # non era ancora inserito in elenco
                if partner_obj.property_payment_term:
                    codpag = partner_obj.property_payment_term.name[0:4]
                else:
                    codpag = ''
                if partner_obj.cod_esenzione_iva:
                    codivaesen=partner_obj.cod_esenzione_iva.description
                else:
                    codivaesen =''
                if partner_obj.vat:
                    piva = partner_obj.vat[2:]
                else:
                    piva = ''
                if partner_obj.fiscalcode :
                    fiscalcode = partner_obj.fiscalcode 
                else:
                    fiscalcode = ''
                if partner_obj.email:
                    email = partner_obj.email
                else:
                    email = ''
                if addr.province.name:
                    prov = addr.province.name
                else:
                    prov = ''
                if addr.street:
                    street =addr.street
                else:
                    street = ''
                if addr.zip:
                    zip =addr.zip
                else:
                    zip = ''
                if addr.phone:
                    phone =addr.phone
                else:
                    phone = ''
                if addr.street:
                    street =addr.street
                else:
                    street = ''
                if addr.fax:
                    fax =addr.fax
                else:
                    fax = ''
                if addr.city:
                    city =addr.city
                else:
                    city = ''
                if addr.mobile:
                    mobile =addr.mobile
                else:
                    mobile = ''
                    
                
                
                
                riga_cli = {
                            'partner_id':partner_obj.id,
                            'flagclifor':'C',
                            'flagnew':'V',
                            'codice':partner_obj.ref,
                            'ragsoc':partner_obj.name[:40],
                            'ragsoc2':" "*30,
                            'indirizzo':street,
                            'cap':zip,
                            'localita':city,
                            'prov':prov,
                            'telefono':phone,
                            'fax':fax,
                            'flagperfis':"N",
                            'flagsesso':'',               
                            'dtnascita':" "*8,
                            'luogona':" "*30,
                            'provna':" "* 2,
                            'codfiscale':fiscalcode,
                            'piva':piva,
                            'sottoconto':conto_partner,
                            'flagpartite':'S',
                            'flagscadenze':'S',
                            'codpag':codpag,
                            'codivaesen':codivaesen,
                            'mese1ecluso':'0'*2,
                            'mese2ecluso':'0'*2,
                            'giornoescluso':'0'*2,
                            'cell':mobile,
                            'indinternet':' '* 40,
                            'email':email,
                            }
                #import pdb;pdb.set_trace()    
                id_rec = tmpfileadclifor_obj.create(cr,uid,riga_cli)
         

            #out = base64.encodestring(File)    
        
        if errori:
            for e in errori:
                print e
        
        return errori
    
    def formatta_num(self,cr,uid,numero,lung):
        s1 = str(round(numero,2)).rjust(lung,"0")
        return s1.replace('.', ',')
                   
        
        return True # da aggiustare



 

GenFileadprinot_Doc()


class tmpfileadprinot(osv.osv):
    _name = 'tmpfileadprinot'
    _description = 'File Temporaneo di prima nota per Ad-Hoc'
    _columns = {
                'numriga':fields.integer("Progressivo di riga file asci"),
                'numreg':fields.integer("Numero singola registrazione"),
                'datreg':fields.char("data registrazione",size = 8),
                'causale':fields.char("Codice Causale",size = 10),
                'dtcompiva':fields.char("data competenza iva",size = 8),
                'numdoc':fields.integer("Numero documento"),
                'alfadoc':fields.char("Alfa doc eventuale",size = 2),
                'dtdoc':fields.char("data documento",size = 8),
                'numprot':fields.integer("Numero Protocollo"),
                'note':fields.char("note",size = 45),
                'sottoconto':fields.char("Sottoconto",size = 10),
                'testcf':fields.char("Test Cliente Fornitore ",size = 1),
                'codclifor':fields.char("Codice Cliente",size = 10),
                'piva':fields.char("partita iva",size = 12),
                'codiceiva':fields.char("Codice iva",size = 10),
                'imponibile':fields.char("Imponibile",size = 15),
                'impodare':fields.char("Importo dare",size = 15),
                'impoavere':fields.char("Importo Avere",size = 15),
                'valuta':fields.char("Valuta",size = 10),
                'cambio':fields.char("Cambio",size = 12),
                'diffiva':fields.char("Differenza Iva",size = 4),
                'codpag':fields.char("Pagamento",size = 10),
                'flagintra':fields.char("Flag Intra",size = 1),
                'dtdiversa':fields.char("data pag diversa",size = 8),
                'cotropatita':fields.char("Contropartita",size = 10),
                'cliforcontrop':fields.char("Contropartita cliente fornitore",size = 10),
                'impregval':fields.char("Importo registrazione in valuta",size = 15),
                
                
                
                }
    
    def pulisce(self,cr,uid,ids,context=False):
        ids =self.search(cr,uid,[])
        if ids:
                ok = self.unlink(cr,uid,ids) 
        return True
    
    def scrive_file(self,cr,uid,ids,context=False):
        ids = self.search(cr,uid,[])
        file = """"""
        file_name = '/home/openerp/primanota/'+'ADPRINOT.001'       
        for riga in self.browse(cr,uid,ids):
            file += str(riga.numriga).rjust(5, "0")
            file += str(riga.numreg).rjust(5, "0")    
            file += riga.datreg             
            file += riga.causale.ljust(10)[:10]
            file += riga.dtcompiva
            file += str(riga.numdoc).rjust(6, "0")   
            file += riga.alfadoc.ljust(2)[:2]
            file += riga.dtdoc
            file += str(riga.numprot).rjust(6, "0")
            file += riga.note.ljust(45)[:45]
            file += riga.sottoconto.ljust(10)[:10]
            file += riga.testcf.ljust(1)[:1]
            file += riga.codclifor.ljust(10)[:10]
            file += riga.piva.ljust(12)[:12]
            file += riga.codiceiva.ljust(10)[:10]
            file += riga.imponibile
            file += riga.impodare    
            file += riga.impoavere    
            file += riga.valuta.ljust(10)[:10]
            file += riga.cambio
            file += riga.diffiva
            file += riga.codpag.ljust(10)[:10]
            file += riga.flagintra.ljust(1)[:1]
            file += riga.dtdiversa
            file += riga.cotropatita.ljust(10)[:10]     
            file += riga.cliforcontrop.ljust(10)[:10]
            file += riga.impregval    
            file += "\r\n"
        fp = open(file_name, 'wb+');
        fp.write(file);
        fp.close();
        
        return True
    
tmpfileadprinot()



class tmpfileadclifor(osv.osv):
    _name = 'tmpfileadclifor'
    _description = 'File Temporaneo di clienti fornitori per Ad-Hoc'
    _columns = {
                'partner_id': fields.many2one('res.partner', 'Cliente'),
                'flagclifor':fields.char("Flag Cliente Fornitore",size = 1),
                'flagnew':fields.char("Flag Nuovo Variato",size = 1),
                'codice':fields.char("codice",size = 10),
                'ragsoc':fields.char("ragione sociale",size = 40),
                'ragsoc2':fields.char("ragione sociale 2",size = 30),
                'indirizzo':fields.char("indirizzo",size = 35),
                'cap':fields.char("cap",size = 5),
                'localita':fields.char("localita",size = 30),
                'prov':fields.char("provincia",size = 2),
                'telefono':fields.char("telefonoe",size = 18),
                'fax':fields.char("fax",size = 18),
                'flagperfis':fields.char("Flag Persona Fisica S - N",size = 1),
                'flagsesso':fields.char("Flag sesso",size = 1),
                'dtnascita':fields.char("data di nascita ",size = 8),
                'luogona':fields.char("luogo di nascita",size = 30),
                'provna':fields.char("provioncia di nascita",size = 2),
                'codfiscale':fields.char("Codice Fiscasle",size = 16),
                'piva':fields.char("Partita iva",size = 12),
                'sottoconto':fields.char("sottoconto",size = 10),
                'flagpartite':fields.char("Flag partite S-N",size = 1),
                'flagscadenze':fields.char("Flag scadenze S-N",size = 1),
                'codpag':fields.char("Codice Pagamento",size = 10),
                'codivaesen':fields.char("codice iva di esenzione",size = 10),
                'mese1ecluso':fields.char("primo mese escluso",size = 2),
                'mese2ecluso':fields.char("secondo mese escluso",size = 2),
                'giornoescluso':fields.char("giorno escluso",size = 2),
                'cell':fields.char("cellulare",size = 18),
                'indinternet':fields.char("indirizzo internet",size = 40),
                'email':fields.char("email",size = 40),
                
                
                
}

                
    def pulisce(self,cr,uid,ids,context=False):
        ids =self.search(cr,uid,[])
        if ids:
                ok = self.unlink(cr,uid,ids) 
        return True
    
    def scrive_file(self,cr,uid,ids,context=False):
        ids = self.search(cr,uid,[])
        file = """"""
        file_name = '/home/openerp/primanota/'+'ADCLIFOR.001'       
        for riga in self.browse(cr,uid,ids):
            file += riga.flagclifor
            file += riga.flagnew
            file += riga.codice.ljust(10)[:10]
            file += riga.ragsoc.ljust(40)[:40]    
            file += riga.ragsoc2.ljust(30)[:30]
            file += riga.indirizzo.ljust(35)[:35]
            file += riga.cap.ljust(5)[:5]
            file += riga.localita.ljust(30)[:30]
            file += riga.prov.ljust(2)[:2]
            file += riga.telefono.ljust(18)[:18]    
            file += riga.fax.ljust(18)[:18]
            file += riga.flagperfis.ljust(1)[:1]
            file += riga.flagsesso.ljust(1)[:1]    
            file += riga.dtnascita.ljust(8)[:8]            
            file += riga.luogona.ljust(30)[:30]
            file += riga.provna.ljust(2)[:2]
            file += riga.codfiscale.ljust(16)[:16]
            file += riga.piva.ljust(12)[:12]
            file += riga.sottoconto.ljust(10)[:10]
            file += riga.flagpartite
            file += riga.flagscadenze 
            file += riga.codpag.ljust(10)[:10]
            file += riga.codivaesen.ljust(10)[:10]   
            file += riga.mese1ecluso
            file += riga.mese2ecluso
            file += riga.giornoescluso    
            file += riga.cell.ljust(18)[:18]
            file += riga.indinternet.ljust(40)[:40]
            file += riga.email.ljust(40)[:40]
            file += "\r\n"          
        fp = open(file_name, 'wb+');
        fp.write(file);
        fp.close();
        

        return True
               


tmpfileadclifor()


class EffettiHeader(osv.osv):
    _inherit = "effetti"
    _columns = {
                'flag_exp_adhoc':fields.boolean("Esportato verso Ad-Hoc"),
                }
    

EffettiHeader()

class GenFileadprinot_Riba(osv.osv_memory):
    _name = 'gen_adprinot_riba'
    _description = 'Genera file di prima nota dalle riba  '

    def _get_conti_eff(self,cr, uid, context=None):
       conto_iva  =  self.pool.get('account.account').search(cr,uid,[('code','=','0120001')])[0]       
       return conto_iva

  
    
    _columns = {
                    'dadatasc': fields.date('Da Data Scadenza', required=True ),
                    'adatasc': fields.date('A Data Scadenza', required=True),
                    'contoeff_id':fields.many2one('account.account', "Conto Effetti Attivi", required=True  ),                    
                    }
    _defaults = {
                 'contoeff_id':_get_conti_eff,
                 }
    
    
    def genera_adprinot(self, cr, uid, ids, context=None):    
        par= self.browse(cr,uid,ids)[0]
        riba_head_obj = self.pool.get('effetti')
        tmpfileadprinot_obj = self.pool.get('tmpfileadprinot')
        tmpfileadclifor_obj = self.pool.get('tmpfileadclifor')
        ok = tmpfileadprinot_obj.pulisce(cr,uid,ids)
        ok = tmpfileadclifor_obj.pulisce(cr,uid,ids)
        numero_reg = 0
        if par.dadatasc and par.adatasc and par.adatasc>=par.dadatasc:  
            cerca =[('data_scadenza',">=",par.dadatasc),('data_scadenza',"<=",par.adatasc),('flag_exp_adhoc','=',False)]
            docs_ids = riba_head_obj.search(cr,uid,cerca,order='data_scadenza,name')
            if docs_ids:
                for doc in riba_head_obj.browse(cr,uid,docs_ids):
                    # cicla sui documenti trovati
                        # DOCUMENTO IDONEO ALLA ESPORTAZIONE
                        numero_reg += 1
                        errori = self.scrive_registrazione(cr, uid,ids, doc, numero_reg)
                        ok = riba_head_obj.write(cr,uid,[doc.id],{'flag_exp_adhoc':True})
                if numero_reg > 0:
                    ok = tmpfileadprinot_obj.scrive_file(cr,uid,ids)
                    ok = tmpfileadclifor_obj.scrive_file(cr,uid,ids)
                else:
                    raise osv.except_osv(_('ERRORE !'),_('Non sono presenti Riba per questa selezione'))
                            
            else:                
                raise osv.except_osv(_('ERRORE !'),_('Non sono presenti Riba per questa selezione'))
        else:
               raise osv.except_osv(_('ERRORE !'),_('Devi Selezionare Meglio le Date Documento'))
        return {'type': 'ir.actions.act_window_close'}


    def scrive_registrazione(self,cr,uid,ids,doc,numero_reg):
        errori=[]
        par= self.browse(cr,uid,ids)[0]
        tmpfileadprinot_obj = self.pool.get('tmpfileadprinot')
        tmpfileadclifor_obj = self.pool.get('tmpfileadclifor')
        partner_obj = self.pool.get('res.partner').browse(cr, uid, doc.cliente_id.id)
        numero_riga = 0
        riga = {}
        # scrive il primo record, quello che riguarda il cliente
        numero_riga +=1
        datadoc = doc.righe_scadenze[0].data_documento.replace('-','') 
        datascr =doc.data_scadenza.replace('-','')     
        datasca = doc.data_scadenza[8:10]+'-'+ doc.data_scadenza[5:7]+'-'+doc.data_scadenza[0:4]
        scadid = doc.righe_scadenze[0].scadenza_id.id
        scad_doc_id = self.pool.get('fiscaldoc.header').search(cr,uid,[('name','=',doc.righe_scadenze[0].numero_doc)])
        if not scad_doc_id:
            return False
        fatt_obj = self.pool.get('fiscaldoc.header').browse(cr,uid,scad_doc_id)[0]
        riga['numriga']= numero_riga
        riga['numreg'] = numero_reg
        riga['datreg']= datadoc
        riga['causale']= '036'
        riga['dtcompiva']= datadoc
        #import pdb;pdb.set_trace()
        riga['numdoc'] = fatt_obj.numdoc
        riga['alfadoc'] = " "*2
        riga['dtdoc'] = datadoc
        riga['numprot']= 0
        riga['note'] = "Scadenza  "+datasca+" "+ doc.note
        riga['sottoconto'] =  '0120001'
        riga['testcf'] = ''
        riga['codclifor'] = ''
        riga['piva']= ''
        riga['codiceiva']=''
        riga['imponibile']='0'*15
        riga['impodare'] = self.formatta_num(cr, uid, doc.importo_effetto,15)
        riga['impoavere'] = '0'*15           
        riga['valuta']='6'
        riga['cambio']= "1".rjust(12,"0")
        riga['diffiva'] = "0"*4
        riga['codpag'] = doc.righe_scadenze[0].pagamento.name[0:4]
        riga['flagintra']=""
        riga['dtdiversa']=datascr
        riga['cotropatita'] =""
        riga['cliforcontrop']=""
        riga['impregval'] = "0"*15
        #import pdb;pdb.set_trace()
        id_rec = tmpfileadprinot_obj.create(cr,uid,riga)
# cliente
        numero_riga +=1
        riga['numriga']= numero_riga
        riga['numreg'] = numero_reg
        riga['datreg']= datadoc
        riga['causale']= '036'
        riga['dtcompiva']= datadoc
        riga['numdoc'] = fatt_obj.numdoc
        riga['alfadoc'] = " "*2
        riga['dtdoc'] = datadoc
        riga['numprot']= 0
        riga['note'] = "Scadenza  "+datasca+" "+ doc.note
        conto_partner = self.pool.get('account.account').browse(cr,uid,partner_obj.property_account_receivable.id).code
        riga['sottoconto'] = conto_partner    
        riga['testcf'] = 'C'
        riga['codclifor'] = partner_obj.ref
        if partner_obj.vat:
            riga['piva']= partner_obj.vat[2:]
        else:
            riga['piva']=''
        riga['codiceiva']=''
        riga['imponibile']='0'*15
        riga['impodare'] = '0'*15 
        riga['impoavere'] = self.formatta_num(cr, uid, doc.importo_effetto,15)   
        riga['valuta']='6'
        riga['cambio']= "1".rjust(12,"0")
        riga['diffiva'] = "0"*4
        riga['codpag'] = doc.righe_scadenze[0].pagamento.name[0:4]
        riga['flagintra']=""
        riga['dtdiversa']=datascr
        riga['cotropatita'] =""
        riga['cliforcontrop']=""
        riga['impregval'] = "0"*15
        #import pdb;pdb.set_trace()
        id_rec = tmpfileadprinot_obj.create(cr,uid,riga)
        if errori:
            # ci sono stati degli errori scrive il file
            file = """"""
            for e in errori:
                file += e +  "\r\n"
            file = """"""
            file_name = '/home/openerp/primanota/'+'errori.txt'
            fp = open(file_name, 'wb+');
            fp.write(file);
            fp.close();

            #out = base64.encodestring(File)    
        
        
        
        return True
        
       
            

    def formatta_num(self,cr,uid,numero,lung):
        s1 = str(round(numero,2)).rjust(lung,"0")
        return s1.replace('.', ',')
                  
    
GenFileadprinot_Riba()
    