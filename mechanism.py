# mechanism.py - mechanism class for implementing TX-TL mechanisms
# RMM, 16 Aug 2018
#
# Mechanisms the means by which all reactions in a TX-TL reaction are
# established.  Mechanisms can be overridden to allow specialized
# processing of core reactions (eg, adding additional detail, using
# simplified models, etc.
#
# Mechanisms are established in the following order (lower levels
# override higher levels):
#
# Default extract mechanisms
#   Default component mechanisms
#       Mechanisms passed to Component() [eg DNA Assembly]
#         Mechanisms based to Subcomponent() [eg, DNA elements]
#
# This hierarchy allows reactions to be created without the user
# having to specify any alternative mechanisms (defaults will be
# used), but also allows the user to override all mechanisms used for
# every component (e.g, by giving an alternative transcription
# mechanisms when setting up an extract) or individual mechanisms for
# a given component (by passing an alternative mechanism just to that
# component).
#
# Copyright (c) 2018, Build-A-Cell. All rights reserved.
# See LICENSE file in the project root directory for details.


from warnings import warn
import chemical_reaction_network as crn
import component
# Mechanism class for core mechanisms
class Mechanism:
    """Core mechanisms within a mixture (transcription, translation, etc)

    The Mechanism class is used to impelement different core
    mechanisms in TX-TL.  All specific core mechanisms should be
    derived from this class.

    """
    def __init__(self,name, type = ""):
        self.name = name
        self.type = type
        if type == "":
            warn("Mechanism "+name+" instantiated without a type. This could prevent the mechanism from being inheritted properly.")


    def update_species(self):
        warn("Default Update Species Called for Mechanism ="+str(self.name))
        return []

    def update_reactions(self):
        warn("Default Update Species Called for Mechanism ="+str(self.name))
        return []

    def __repr__(self):
        return self.name

#Helper function to automatically generate Michalis-Menten Type Reactions
#In the Copy RXN version, the Substrate is not Consumed
#Sub+Enz <--> Sub:Enz --> Enz+Prod
class MichalisMentenRXN(Mechanism):
    def __init__(self, name, enzyme, type):
        if isinstance(enzyme, crn.specie):
            self.Enzyme = enzyme
        else:
            raise ValueError("MichalisMentenRXN takes a specie object for its enzyme argument")

        Mechanism.__init__(self, name, type)

    def update_species(self, Sub):
        complex = crn.specie(Sub.type+"_"+Sub.name + ":" +self.Enzyme.type+"_"+self.Enzyme.name, type="complex")
        return [complex]


    def update_reactions(self, Sub, Prod, complex = None, kb = 100, ku = 10, kcat = 1):
        if complex == None:
            complex = crn.specie(Sub.type+"_"+Sub.name + ":" + self.Enzyme.type+"_"+self.Enzyme.name, type="complex")
        # Sub + Enz <--> Sub:Enz
        binding_rxn = crn.reaction(inputs=[Sub, self.Enzyme], outputs=[complex], k=kb, k_rev=ku)
        if Prod != None:
            # Sub:Enz --> Enz + Prod
            cat_rxn = crn.reaction(inputs=[complex], outputs=[Prod, self.Enzyme], k=kcat)
        else: #Degredation Reaction
            # Sub:Enz --> Enz
            cat_rxn = crn.reaction(inputs=[complex], outputs=[self.Enzyme], k=kcat)
        return [binding_rxn, cat_rxn]


#In the Copy RXN version, the Substrate is not Consumed
#Sub+Enz <--> Sub:Enz --> Sub+Enz+Prod
class MichalisMentenCopyRXN(Mechanism):
    def __init__(self, name, enzyme, type):
        if isinstance(enzyme, crn.specie):
            self.Enzyme = enzyme
        else:
            raise ValueError("MichalisMentenCopyRXN takes a specie object for its enzyme argument")

        Mechanism.__init__(self, name, type)

    def update_species(self, Sub):
        complex = crn.specie(Sub.type+"_"+Sub.name + ":" + self.Enzyme.type+"_"+self.Enzyme.name
, type="complex")
        return [complex]


    def update_reactions(self, Sub, Prod, complex = None, kb = 100, ku = 10, kcat = 1):
        if complex == None:
            complex = crn.specie(Sub.type+"_"+Sub.name + ":" + self.Enzyme.type+"_"+self.Enzyme.name, type="complex")
        # Sub + Enz <--> Sub:Enz
        binding_rxn = crn.reaction(inputs=[Sub, self.Enzyme], outputs=[complex], k=kb, k_rev=ku)

        # Sub:Enz --> Enz + Prod + Sub
        cat_rxn = crn.reaction(inputs=[complex], outputs=[Sub, Prod, self.Enzyme], k=kcat)

        return [binding_rxn, cat_rxn]


#Michalis Menten Transcription
#G + RNAP <--> G:RNAP --> G+RNAP+mRNA
class Transcription_MM(MichalisMentenCopyRXN):
    def __init__(self, name = "transcription_mm", rnap = "RNAP"):
        if isinstance(rnap, crn.specie):
            self.rnap = rnap
        elif isinstance(rnap, str):
            self.rnap = crn.specie(name = rnap, type = "protein")
        else:
            raise ValueError("'rnap' parameter must be a string or chemical_reaction_network.specie")

        MichalisMentenCopyRXN.__init__(self = self, name = name, enzyme=self.rnap, type = "transcription")

    def update_species(self, dna, return_transcript = False, return_rnap = False):
        species = []
        if return_rnap:
            species += [self.rnap]

        species += MichalisMentenCopyRXN.update_species(self, dna)
        if return_transcript:
            species += [crn.specie(dna.name, type = "rna")]
        return species

    def update_reactions(self, dna, kb, ku, ktx, complex = None, transcript = None):
        rxns = []

        if transcript == None:
            transcript = crn.specie(dna.name, type="rna")
        rxns += MichalisMentenCopyRXN.update_reactions(self, dna, transcript, complex = complex, kb = kb, ku = ku, kcat = ktx)

        return rxns

#Michalis Menten Translation
#mRNA + Rib <--> mRNA:Rib --> mRNA + Rib + Protein
class Translation_MM(MichalisMentenCopyRXN):

    def __init__(self, name="translation_mm", ribosome="Ribo"):
        if isinstance(ribosome, crn.specie):
            self.ribosome = ribosome
        elif isinstance(ribosome, str):
            self.ribosome = crn.specie(name=ribosome, type="ribosome")
        else:
            raise ValueError("'ribosome' parameter must be a string or chemical_reaction_network.specie")
        MichalisMentenCopyRXN.__init__(self=self, name=name, enzyme=self.ribosome, type = "translation")

    def update_species(self, transcript, return_protein=False, return_ribosome = False):
        species = []
        if return_ribosome:
            species = [self.ribosome]
        species += MichalisMentenCopyRXN.update_species(self, transcript)
        if return_protein:
            species += [crn.specie(transcript.name, type="protein")]
        return species

    def update_reactions(self, transcript, kb, ku, ktl, complex=None, protein=None):
        rxns = []

        if protein == None:
            protein = crn.specie(transcript.name, type="protein")
        rxns += MichalisMentenCopyRXN.update_reactions(self, transcript, protein, complex=complex,
                                                  kb=kb, ku=ku,
                                                  kcat=ktl)
        return rxns

#Michalis Menten mRNA Degredation by Endonucleases
#mRNA + Endo <--> mRNA:Endo --> Endo
class Degredation_mRNA_MM(MichalisMentenRXN):
    def __init__(self, name="rna_degredation_mm", nuclease="RNAase"):
        if isinstance(nuclease, crn.specie):
            self.nuclease = nuclease
        elif isinstance(nuclease, str):
            self.nuclease = crn.specie(name=nuclease, type="protein")
        else:
            raise ValueError("'nuclease' parameter requires a chemical_reaction_network.specie or a string")
        MichalisMentenRXN.__init__(self=self, name=name, enzyme=self.nuclease, type = "rna_degredation")

    def update_species(self, rna, return_nuclease = False):
        species = []
        if return_nuclease:
            species += [self.nuclease]
        species += MichalisMentenRXN.update_species(self, rna)
        return species

    def update_reactions(self, rna, kb, ku, kdeg, complex=None):
        rxns = []
        rxns += MichalisMentenRXN.update_reactions(self, rna, Prod=None, complex=complex,
                                                      kb=kb, ku=ku,
                                                      kcat=kdeg)
        return rxns


class One_Step_Cooperative_Binding(Mechanism):
    def __init__(self, name="one_step_cooperative_binding", type="cooperative_binding"):
        Mechanism.__init__(self, name, type)

    def update_species(self, binder, bindee, cooperativity = 1, **kwords):
        complex = crn.specie(binder.type +"_" + str(cooperativity) + "x_" + binder.name + ":" + bindee.type + "_" + bindee.name, type="complex")
        return [complex]

    def update_reactions(self, binder, bindee, kb, ku, cooperativity = 1, **kwords):
        complex = crn.specie(binder.type +"_" + str(cooperativity) + "x_" + binder.name + ":" + bindee.type + "_" + bindee.name, type="complex")

        rxns = []
        rxns += [crn.reaction(inputs = [binder, bindee], outputs = [complex], input_coefs=[cooperativity, 1], output_coefs=[1], k = kb, k_rev=ku)]
        return rxns

class Two_Step_Cooperative_Binding(Mechanism):
    def __init__(self, name = "two_step_cooperative_binding", type="cooperative_binding"):
        Mechanism.__init__(self, name, type)

    def update_species(self, binder, bindee, cooperativity = 2):
        n_mer = crn.specie(str(cooperativity)+"x_"+bindee.name, type = "complex")
        complex = crn.specie(binder.type + "_" + n_mer.name + ":" + bindee.type + "_" + bindee.name,
                                 type="complex")

        return [complex, n_mer]

    #Returns reactions:
    # cooperativity binder <--> n_mer, kf = kb1, kr = ku1
    # n_mer + bindee <--> complex, kf = kb2, kr = ku2
    def update_reactions(self, binder, bindee, kb, ku, cooperativity = 2):

        if len(kb) != len(ku) != 2:
            raise ValueError("kb and ku must contain 2 values each for two-step binding")
        kb1, kb2 = kb
        ku1, ku2 = ku

        n_mer = crn.specie(str(cooperativity) + "x_" + bindee.name, type="complex")
        complex = crn.specie(binder.type + "_" + n_mer.name + ":" + bindee.type + "_" + bindee.name,
                             type="complex")

        rxns = [crn.reaction(inputs = [binder], outputs = [n_mer], input_coefs=[cooperativity], output_coefs=[1], k = kb1, k_rev=ku1),
                crn.reaction(inputs = [n_mer, bindee], outputs = [complex], k = kb2, k_rev=ku2)]

        return rxns
