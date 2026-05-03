# Eris FALSECOLORS
## Noncryptographic Semantic Transformation for Deniable Document Protection

**Working Paper**
**Author: River Caudle**
**Revision: 3.0**
**Date: May 2026**

---

> *"False colors" (faux pavillon): the historical naval practice of
> flying a different nation's flag to approach without suspicion.
> The ship is real. The flag is real. Only the allegiance is false.
> The cargo remains below deck.*

> *Eris: Greek goddess of discord. She does not destroy. She
> recontextualizes. The apple was real. The inscription was real.
> Only the audience's interpretation was engineered.*

---

## Abstract

This paper introduces FALSECOLORS, a noncryptographic security primitive that protects sensitive textual documents through structure-preserving semantic domain transformation. Unlike encryption, which renders data incomprehensible and thereby signals its value, FALSECOLORS produces output that is fully comprehensible, domain-coherent, and self-consistent in an unrelated cover domain. The sensitive content is recoverable only through possession of compact key artifacts. Without the keys, cover documents stand alone as legitimate documents in their surface domains, with no statistical, structural, or information-theoretic signal that another reading exists.

The system comprises a pre-processing layer and four methods of increasing capability. The Identifier Encoding Layer separates technical identifiers from their operational context. Method 1 (Recolor) transforms documents through static vocabulary mapping. Method 2 (Split) distributes document vocabulary across multiple cover documents for multi-artifact security. Method 3 (Pad) enables persistent deniable communication channels through a reusable shared secret. Method 4 (Dynamic Shift) uses a local transformer model to perform domain translation with zero static tables, generating per-document mappings on the fly.

A reference implementation is presented as an LLM middleware proxy that transparently encodes outbound queries and decodes inbound responses, enabling users to interact with frontier cloud AI systems while the cloud provider sees only innocuous cover-domain conversations. A simplified user interface reduces the entire system to three inputs (source text, passphrase, cover topic) producing a single self-contained output document with the encrypted mapping embedded. A sanitize mode provides confidentiality without deniability, replacing all domain-specific tokens with opaque labels and shifting numeric values by a deterministic content-derived constant, enabling cloud LLM analysis of sensitive findings without exposing the identity of the system under assessment.

The security basis is information-theoretic rather than computational. There is no ciphertext to attack. There is no encrypted container to identify. The protection is not a lock on a door. It is the absence of a door.

---

## 1. Introduction

### 1.1 Problem Statement

Sensitive documents must be stored, transmitted, and referenced over time. Encryption protects documents in transit and, with proper key management, at rest. However, encryption has a fundamental weakness as a storage-time protection: encrypted artifacts advertise their value. A password-protected archive, an encrypted disk image, or a PGP-encrypted file all signal to an adversary that something worth protecting is inside. This attracts exactly the attention the protection is meant to prevent.

In adversarial environments, including litigation discovery, insider threat scenarios, device seizure, cloud storage compromise, and nation-state surveillance, the presence of encrypted artifacts can trigger compelled disclosure, rubber-hose cryptanalysis, or simply prioritized targeting. The encryption may hold, but its presence has already conceded that a secret exists.

This problem is acute in two contexts. First, operational technology security, where penetration test findings describe exactly how to compromise physical safety systems. A finding that documents unauthenticated write access to safety interlock registers at a chemical facility is, if intercepted, an attack playbook. The consequence of interception is not data breach. It is potential physical harm.

Second, cloud AI interaction, where organizations need frontier-grade AI reasoning on sensitive data but cannot expose that data to cloud providers. Current approaches require custom inference layers, specialized edge hardware, or cryptographic schemes that prevent the AI from reasoning on the data natively. FALSECOLORS enables unmodified cloud AI systems to reason on sensitive content by presenting it in an innocuous cover domain that preserves the relational structure the AI needs for analysis.

### 1.2 The False Colors Principle

FALSECOLORS provides a protection mechanism where the protected artifact does not appear to be protected. The sensitive document is replaced by one or more innocuous documents that are fully legitimate in their surface domain. An adversary who obtains the cover documents has no reason to investigate further because there is nothing that appears to require investigation.

The insight is that the security of natural language documents can be based on semantic domain transformation rather than mathematical encryption. A document's meaning is carried by two independent components: its relational structure (the logical argument, the causal chains, the measurement relationships) and its vocabulary (the domain-specific terms that give the structure its specific interpretation). Changing the vocabulary while preserving the structure produces a new document that is equally coherent but describes a completely different subject.

The ship is real. The flag is real. Only the allegiance is false.

This is analogous to rubberhose-resistant deniable encryption (Canetti et al., 1997), but stronger. Deniable encryption produces two valid plaintexts from one ciphertext, but the ciphertext still exists as an artifact that demands explanation. FALSECOLORS eliminates the ciphertext entirely. Both the cover document and the sensitive document are valid texts. The mapping between them exists only as external key artifacts that can be destroyed, leaving all cover documents freestanding forever.

---

## 2. Theoretical Foundation

### 2.1 Documents as Relational Structures

A document D can be modeled as a labeled directed graph G = (V, E, L) where V is a set of semantic positions (slots in the argument), E is a set of directed edges representing relational dependencies (causation, measurement, containment, sequence, modification), and L: V -> T is a labeling function that assigns a token from vocabulary T to each position.

The comprehensibility of D arises from two independent properties. First, the coherence of E: the relational structure must form valid logical chains (causes precede effects, measurements reference measurable quantities, conditionals connect to consequences). Second, the domain-consistency of L: the vocabulary must be internally consistent (a document about brewing should not contain metallurgical terms unless contextually justified).

The critical insight is that these two properties are separable. An edge "X measures Y" is comprehensible regardless of whether X is "pressure gauge" or "humidity sensor." The statement "if X exceeds T, activate Z" is a valid conditional regardless of whether X is "reactor pressure," T is "185 PSI," and Z is "emergency shutdown valve," or X is "fermenter carbonation," T is "4.2 volumes CO2," and Z is "batch rejection gate." The relational structure is domain-independent. The vocabulary is domain-specific.

This separability is the foundation of FALSECOLORS. If the relational structure of a document can be preserved while the vocabulary is replaced, the result is a new document that is equally coherent, equally logical, and equally readable, but describes a completely different subject.

### 2.2 Domain Isomorphism

Two domain vocabularies T_a and T_b are isomorphic with respect to a relational structure E if there exists a bijective mapping M: T_a -> T_b such that for every edge (u, v, r) in E, the relabeled edge (M(L(u)), M(L(v)), r) is semantically valid in domain B.

Formally, let R be the set of relational types (measures, causes, contains, exceeds, activates, requires, etc.). A domain isomorphism M preserves R-validity:

    For all (u, v, r) in E where r in R:
    if (L(u), L(v), r) is R-valid in domain A,
    then (M(L(u)), M(L(v)), r) is R-valid in domain B.

Informally: if "boiler pressure exceeds threshold" is a valid statement in domain A, and M maps "boiler" to "fermenter," "pressure" to "carbonation," and "threshold" to "checkpoint," then "fermenter carbonation exceeds checkpoint" must be a valid statement in domain B.

Domain isomorphisms exist naturally between domains that describe physical systems with analogous structures. Industrial process control and brewing both involve vessels, measurements, thresholds, control loops, safety interlocks, and consequence chains. Agriculture, water treatment, HVAC, and pharmaceutical manufacturing share these patterns. The isomorphisms are not coincidental; they reflect the shared physics and engineering principles underlying these domains.

Not all domain pairs admit useful isomorphisms. A domain pair requires sufficient structural overlap to preserve the relational edges of typical documents. Domains describing physical systems map well to other physical-system domains. Abstract domains (legal reasoning, philosophical argument) may not map cleanly to concrete domains without breaking R-validity.

A specific boundary case arises with purely computational vulnerabilities. A buffer overflow in a protocol stack, a race condition in a state machine, or a type confusion in a parser depends on relational structures (memory layout, execution sequence, type hierarchy) that have no direct analogue in physical-process domains like brewing or agriculture. These computational-structural relationships reduce the semantic entropy of the document and constrain the set of viable cover domains.

For such documents, viable cover domains must be drawn from other computational contexts. A buffer overflow finding maps more naturally to a document about a data processing pipeline, a database query optimizer, or a game engine than to a brewery audit. The relational structures of computational systems (input, processing, overflow, corruption, consequence) are shared across computational domains even when they do not map to physical-system domains. Method 4 (Dynamic Shift) handles this case most naturally because the local LLM can identify the appropriate computational cover domain from the source content without a pre-built mapping table. Methods 1 and 3 require purpose-built mapping tables for computational-to-computational domain pairs.

### 2.3 The Embedding Hypersphere

Modern language models represent each token in their vocabulary as a dense vector in R^D, where D is the embedding dimensionality (typically 768, 1536, or higher). The complete set of token vectors forms the embedding matrix, a V-by-D matrix where V is the vocabulary size (typically 30,000 to 100,000 tokens).

In practice, embedding vectors are typically L2-normalized, meaning every token vector has unit length. This places all tokens on the surface of a unit hypersphere in R^D. The semantic similarity between two tokens is measured by cosine similarity, which on the unit hypersphere is simply the dot product of their vectors, equivalently the cosine of the angle between them.

This geometry has several properties essential to FALSECOLORS:

**The embedding matrix is fully populated.** Every row in the V-by-D matrix corresponds to exactly one token. There are no empty rows, no unused indices. Any discrete index in the matrix is a valid token. On the continuous hypersphere surface, a given point may fall between token positions, but in high dimensions with tens of thousands of tokens, the average angular distance to the nearest token is small. For practical purposes, every region of the sphere that a domain cluster occupies is densely populated with valid tokens.

**Semantic relationships are geometric relationships.** Tokens with similar meanings cluster together on the sphere. "Boiler," "reactor," "furnace," and "vessel" occupy nearby positions. "Pressure," "temperature," "flow rate," and "level" occupy a different nearby cluster. The angular distance between clusters encodes the semantic distance between concepts.

**Analogical relationships are vector operations.** The classic finding of Mikolov et al. (2013) that vector("king") - vector("man") + vector("woman") ≈ vector("queen") reflects a deeper property: the geometric structure of the embedding space encodes relational patterns as directions. The direction from "man" to "woman" is approximately the same as the direction from "king" to "queen." This regularity extends to domain relationships: the direction from "boiler" to "pressure" may approximate the direction from "fermenter" to "carbonation."

**Domain clusters exhibit approximate internal isomorphism.** The OT/ICS cluster and the brewing cluster have similar internal geometry because both domains describe physical systems using parallel relational structures (measurement, control, threshold, consequence). This approximate isomorphism is not engineered; it is a natural consequence of how language models learn from corpora where these domains are described using structurally similar language.

### 2.4 Rotation as Isometric Mapping

A rotation R in SO(D) (the special orthogonal group in D dimensions) is a linear transformation that preserves all distances and angles. On the unit hypersphere, rotation has the following properties:

**Isometry.** For any two points p and q on the sphere, the angular distance between R(p) and R(q) equals the angular distance between p and q. All pairwise distances in a set of points are invariant under rotation. This means the relational structure encoded by geometric distances is perfectly preserved.

**Bijectivity.** Rotation is a bijection from the sphere to itself. Every point maps to exactly one other point, and every point is the image of exactly one other point. No information is created or destroyed.

**Group structure.** Rotations compose (applying R1 then R2 is equivalent to applying R1*R2). Every rotation has an inverse (R^{-1} undoes R exactly). The identity rotation maps every point to itself. This provides the mathematical foundation for chaining transformations and for exact recovery.

**No statistical signature.** A rotation is a symmetry of the sphere. The uniform distribution on the sphere is invariant under rotation. This means that the distribution of pairwise distances in a set of rotated tokens is identical to the distribution before rotation. No statistical test based on distributional properties can detect that a rotation has occurred, because rotation does not change any distributional property. This is the information-theoretic basis of FALSECOLORS deniability.

The practical application: if the OT domain cluster is rotated onto the brewing domain cluster, every OT term moves to a new position on the sphere. The nearest token at that new position is a candidate mapping target. Because the rotation preserved all internal distances, the geometric relationships within the OT cluster (which encode semantic relationships between OT terms) are preserved in the mapped positions (which now sit within the brewing cluster).

### 2.5 Quantization and Snap-to-Nearest-Neighbor

The rotation maps each source token to a new continuous position on the hypersphere. This position will generally not coincide exactly with any target vocabulary token. The nearest vocabulary token must be found and substituted, a process called "snap-to-nearest-neighbor" or quantization.

Quantization introduces error. The angular distance between the rotated position and the snapped token is the quantization error epsilon for that token. If epsilon is zero for all tokens, the mapping is exact. If epsilon is large for some tokens, the relational structure is distorted: two tokens that were angularly close in the source domain may snap to targets that are not angularly close in the target domain.

**Why epsilon is bounded in high dimensions.** On a D-dimensional hypersphere with V uniformly distributed points, the expected angular distance to the nearest neighbor decreases as D and V increase. For D = 768 and V = 50,000, the average nearest-neighbor distance is very small. This means that most rotated positions land close to a valid token. The quantization error is typically small enough that the semantic relationships encoded by angular distances are approximately preserved.

**Why approximate preservation is sufficient.** FALSECOLORS does not require bit-perfect geometric preservation. It requires that the domain isomorphism property holds: that the snapped tokens form valid statements in the target domain. A small quantization error that maps "reactor" to "fermenter" rather than "autoclave" is acceptable as long as the resulting statement is domain-coherent. The requirement is semantic validity, not geometric perfection.

**The curation step absorbs residual error.** After rotation and snap, the resulting raw mapping is reviewed. Tokens where snap produced a semantically inappropriate target (e.g., "pressure" snapped to "stress" rather than "carbonation") are manually corrected. The curation step is where the mapping transitions from a geometric approximation to an exact, validated domain isomorphism. The rotation did the heavy lifting of identifying candidate correspondences; curation polishes the result.

**Bijectivity collisions.** Quantization error and bijectivity violation are distinct failure modes. Quantization error maps a source token to the wrong target. A bijectivity collision maps two different source tokens to the same target, breaking the injectivity required for exact inverse recovery. If both "pressure" and "stress" snap to "carbonation" in the target domain, the inverse mapping cannot determine which source term a given instance of "carbonation" represents.

Collisions are detected mechanically during the curation step: any target token appearing more than once in the raw mapping is a collision. Resolution strategies include reassigning one of the colliding sources to the second-nearest target, splitting the target vocabulary by introducing qualified variants (e.g., "carbonation level" vs. "carbonation stress"), or expanding the target domain vocabulary to provide more distinct landing points. The collision rate is inversely proportional to the ratio of target vocabulary size to source vocabulary size. A target domain with a richer vocabulary than the source domain will have fewer collisions.

In the formal model (Section 2.13), bijectivity is assumed. The Caudle Theorem holds only for bijective mappings. In practice, the curation step enforces bijectivity by resolving all detected collisions before the mapping is finalized. The formal guarantee applies to the curated mapping, not to the raw snap output.

### 2.6 The Lattice Vocabulary

For applications requiring zero quantization error (where even approximate mapping is unacceptable), the vocabulary can be constrained to a subset that forms a regular lattice in the embedding space.

A lattice is a set of points with uniform spacing. If the working vocabulary is restricted to tokens that occupy positions forming a symmetric lattice on the hypersphere, and the rotation angle is restricted to values that map lattice points exactly onto other lattice points, then quantization error is identically zero. Every rotated point lands exactly on a valid token.

Constructing such a lattice requires identifying a subset of the full vocabulary (perhaps 2,000 to 5,000 tokens) whose embedding positions approximate a regular geometric structure. This is feasible because the working vocabulary for any specific domain pair is much smaller than the full model vocabulary, and Self-Organizing Maps or similar topology-preserving projections can organize a curated subset into a near-regular structure.

The tradeoff is expressiveness. Constraining the vocabulary limits the range of documents that can be represented. For technical documents with specialized but finite vocabulary (pentest findings, audit reports, compliance assessments), this constraint is acceptable. For general prose, it is too restrictive.

The lattice vocabulary is most relevant to Method 1 (Recolor) and Method 3 (Pad) where static mappings are used repeatedly. For Method 4 (Dynamic Shift), the local LLM handles quantization implicitly and the lattice concept does not apply.

### 2.7 Function Word Subspace Decomposition

Not all tokens in a document are domain-specific. Function words ("the," "is," "between," "must," "however"), logical connectives ("if," "then," "because," "therefore"), and quantifiers ("each," "every," "all," "some") are domain-neutral. They must pass through the domain transformation unchanged to preserve grammatical structure and logical coherence.

In high-dimensional embedding space, function words and content words occupy separable subspaces. Function words cluster along different principal components than domain-specific content words. This is not accidental; it reflects the fundamentally different distributional behavior of function words (which appear uniformly across all domains) versus content words (which appear preferentially within specific domains).

This separability enables a critical optimization: the rotation can be decomposed into a component that acts on the content-word subspace and an identity component on the function-word subspace. Formally, if the embedding space R^D can be decomposed as R^D = C + F where C is the content subspace and F is the function subspace, then the rotation R can be constructed as R = R_c + I_f, where R_c rotates within C and I_f is the identity on F.

Under this decomposition, function words remain exactly fixed. Content words rotate to their target-domain equivalents. Grammatical structure is perfectly preserved. The cover document uses the same prepositions, articles, conjunctions, and logical connectives as the source document, which is precisely what makes it read naturally.

In the static implementation (Methods 1 and 3), this decomposition is achieved trivially: function words are simply excluded from the mapping table and pass through unchanged. In the geometric formulation, the decomposition provides the formal justification for why this exclusion preserves document coherence.

### 2.8 Distinction from Steganography

FALSECOLORS is not steganography, and the distinction is fundamental to understanding its security properties.

**Steganography** hides arbitrary data inside innocuous cover media. The hidden data and the cover are unrelated. A steganographic image looks like a normal photograph, but specific pixel values encode a hidden message. The hidden message could be anything: it has no relationship to the photograph's content. Detection methods work by identifying statistical anomalies in the cover media that result from the embedding process: the pixel distribution of a steganographic image differs subtly from a natural photograph.

**FALSECOLORS** does not hide data inside cover media. The cover document IS the sensitive content, expressed in a different vocabulary. There is nothing hidden. There is nothing embedded. The cover document and the sensitive document are the same relational structure with different labels. An observer who reads the cover document receives the complete logical argument, the complete causal chain, the complete set of relationships. They simply receive it in a domain they weren't looking for.

This distinction has three consequences:

First, statistical detection methods that work against steganography do not apply to FALSECOLORS. Steganographic detection exploits the fact that embedding hidden data perturbs the statistical properties of the cover medium. FALSECOLORS does not perturb anything. The cover document's statistical properties (n-gram frequencies, transition probabilities, distributional characteristics) are natural for its domain because the relational structure that determines these properties is preserved exactly. There is no perturbation to detect.

Second, the cover medium in steganography is disposable. It is chosen for convenience and discarded after extraction. The cover document in FALSECOLORS is meaningful. It is a coherent, useful document in its own domain. It can be published, cited, acted upon. A brewery quality audit produced by FALSECOLORS is a legitimate brewery quality audit with valid recommendations and accurate structural logic.

Third, steganographic capacity is limited by the cover medium's ability to absorb hidden data without detectable distortion. FALSECOLORS has no capacity limit because it does not embed data. A 100-page sensitive document produces a 100-page cover document. The "capacity" is 1:1 by construction.

### 2.9 Distinction from Deniable Encryption

Deniable encryption (Canetti et al., 1997) produces ciphertext that can be decrypted to different valid plaintexts depending on which key is provided. Under coercion ("give me the key"), the user provides a decoy key that produces an innocuous plaintext. The real key, if it exists, produces the sensitive plaintext. The adversary cannot prove that the decoy key is not the only key.

FALSECOLORS provides a strictly stronger deniability guarantee. The differences:

**No ciphertext artifact.** Deniable encryption produces a ciphertext object that is visibly encrypted. The ciphertext itself is evidence that something is being hidden. The adversary knows a secret exists; they simply cannot determine which plaintext is real. FALSECOLORS produces no ciphertext. The cover document is plaintext. There is no encrypted object to demand decryption of. The adversary does not know a secret exists.

**No key coercion surface.** Deniable encryption is vulnerable to coercion because the adversary knows keys exist (the ciphertext proves it). They can demand keys. The system's security depends on the adversary accepting the decoy key as genuine. FALSECOLORS has no key to coerce. The mapping can be destroyed. Once destroyed, the cover document is a brewery audit. There is no evidence that a mapping ever existed. The adversary cannot demand something whose existence they cannot demonstrate.

**No computational assumptions.** Deniable encryption relies on computational hardness assumptions (the adversary cannot brute-force all possible keys). FALSECOLORS relies on information-theoretic properties: a self-consistent document in a coherent domain is indistinguishable from a native document in that domain by any method, computational or otherwise. The deniability holds against adversaries with unlimited computational resources.

**Multiple valid covers.** In deniable encryption, the number of valid decryptions is constrained by the encryption scheme (typically two: real and decoy). In FALSECOLORS, the same sensitive document can be transformed into unlimited cover documents in different domains, each with its own mapping. An adversary who suspects one cover and inverts it finds the sensitive content but cannot determine whether other covers exist elsewhere. The sensitive content may be simultaneously protected as a brewery audit, a garden maintenance guide, and a community theater production log.

The analogy to "rubberhose cryptography" (the colloquial term for coercion-resistant encryption) is precise: FALSECOLORS is the rubberhose-resistant system for plaintext. There is no rubber hose that works because there is no key to extract. The mapping is the key, and the mapping can be destroyed. After destruction, the cover document is indistinguishable from a native document in its domain, and the sensitive document either exists in the user's memory or does not exist at all.

### 2.10 The AI Passthrough Property

The most operationally significant property of FALSECOLORS is that cover documents can be processed by unmodified cloud AI systems with valid analytical results.

A cloud LLM that receives a FALSECOLORS cover document processes it as a native document in the cover domain. The LLM does not detect transformation because there is no transformation artifact to detect. The document is a well-formed document in a domain the LLM understands. The LLM applies its full reasoning capabilities to the cover-domain content.

The analytical outputs are valid in the source domain because the relational structure was preserved. If the cover document describes a brewery quality control issue where "unauthenticated parameter writes allow arbitrary modification of carbonation thresholds," the LLM will recommend "implementing authentication, restricting access, and enabling modification tracking." When these recommendations are inverse-mapped, they become "implementing authentication, restricting access, and enabling change detection" in the OT domain. The recommendations are structurally identical. The domain shift is transparent to the analytical process.

This property exists because language models reason over relational structures, not over domain labels. The LLM's reasoning engine operates on the edges of the document graph (causation, measurement, threshold, consequence), not on the specific vocabulary. When the vocabulary changes but the edges remain the same, the reasoning produces structurally equivalent outputs.

The AI passthrough property has no precedent in the data protection literature. Encryption prevents AI processing entirely (the data is incomprehensible). Homomorphic encryption allows computation on encrypted data but with massive computational overhead and limited operation support. Tokenization and anonymization preserve processability but leak structural information. FALSECOLORS provides full processability with full structural protection: the AI can reason on the data, but the data it reasons on describes the wrong domain.

### 2.11 From Geometry to Implementation

The theoretical foundation maps to four implementation strategies with increasing capability and increasing compute requirements:

**Static lookup (Methods 1, 3).** The geometric discovery process (rotation, snap, curation) is performed once during mapping construction. The result is a static bijective lookup table. At runtime, encoding and decoding are dictionary substitutions: O(n) in document length, no compute beyond string matching. The geometry informed the mapping; the mapping does the work.

**Semantic secret sharing (Method 2).** The mapping is not applied as a vocabulary shift but as a vocabulary distribution across cover documents. The geometry is relevant only insofar as it helps construct cover documents with appropriate vocabulary. At runtime, encoding is position-index construction: O(n*m) where n is document length and m is cover document length.

**Local transformer (Method 4).** The geometric isomorphism is exploited implicitly. The local model has internalized both domain clusters during training. Its embedding weights already encode the approximate isomorphism. When asked to "rewrite this OT finding as a brewery audit," the model traverses the isomorphism using its own geometric representation. No explicit rotation or snap occurs. The model outputs the mapping as a byproduct of its translation.

**Constrained lattice (theoretical).** For applications requiring provably zero quantization error, the vocabulary is constrained to a regular lattice and the rotation angles are restricted to lattice-preserving values. This provides bit-perfect geometric preservation at the cost of expressiveness. Primarily of theoretical interest; the curation step in Methods 1 and 3 achieves the same practical outcome without the vocabulary constraint.

### 2.12 Security Properties

**Deniability (information-theoretic).** The cover document is statistically indistinguishable from a native document in the cover domain. The relational structure (which determines n-gram distributions, transition probabilities, and all higher-order distributional statistics) is preserved exactly. The vocabulary is internally consistent for the cover domain. No statistical test, no machine learning classifier, and no human domain expert can identify the cover document as transformed, because the transformation preserves precisely the properties that tests, classifiers, and experts evaluate.

**Key compactness.** Key artifacts range from a single passphrase (Simple Interface) to a shared secret (Method 3) to a static mapping table (Methods 1, 3: typically 5-50KB) to a per-document JSON mapping (Methods 2, 4: typically 2-100KB). All are small enough to store, transmit, memorize (partially), and destroy easily.

**Perfect recovery.** For all methods, applying the inverse transformation with the correct key recovers the original document exactly. This is guaranteed by the bijectivity of the mapping (Methods 1, 3, 4) or by the completeness of the position key (Method 2).

**AI passthrough.** Cover documents are processable by unmodified cloud AI systems. Analytical results in the cover domain, when inverse-mapped, yield valid results in the source domain. The cloud AI requires no modification, no custom inference layer, and no awareness that transformation occurred.

**Composability.** Transformations chain. A document shifted A->B->C requires both keys for full recovery. Compromise of the outer key yields a plausible document in the intermediate domain. Each layer adds deniability.

**Forward secrecy (Method 2, 4).** Per-document keys provide forward secrecy: compromise of one document's key does not expose any other document. Methods 1 and 3 use reusable keys and do not provide forward secrecy; regular key rotation mitigates this.

### 2.13 The Caudle Semantic Secrecy Theorem

Shannon (1949) proved that the one-time pad achieves perfect secrecy for bit strings: if the key K is drawn uniformly at random from the key space and used only once, then the ciphertext C provides zero information about the plaintext P. Formally, P(P = p | C = c) = P(P = p) for all p, c. The ciphertext does not update the adversary's prior belief about the plaintext.

FALSECOLORS admits an analogous result for semantic transformations on labeled relational graphs.

**Definition 2.13.1 (Semantic Document).** A semantic document D = (G, L) consists of a relational graph G = (V, E) and a labeling function L: V -> T assigning tokens from vocabulary T to graph positions.

**Definition 2.13.2 (Domain Isomorphism Space).** For relational graph G and domain vocabularies T_a, T_b, define S(G, T_a, T_b) as the set of all bijective labelings M: T_a -> T_b such that for every edge (u, v, r) in E, the relabeled edge (M(L(u)), M(L(v)), r) is R-valid in T_b. This is the space of all valid domain isomorphisms for graph G between the two vocabularies.

**Definition 2.13.3 (Semantic Transformation).** For source document D = (G, L_a) with L_a: V -> T_a, and isomorphism M drawn from S(G, T_a, T_b), the cover document is C = (G, M ∘ L_a), which is the same graph with relabeled vocabulary.

**Theorem 2.13.4 (Caudle Semantic Secrecy Theorem).** If M is drawn uniformly at random from S(G, T_a, T_b) and used only once, then for any cover document C and any candidate source document D' sharing relational graph G:

    P(source = D' | cover = C) = P(source = D')

The cover document provides zero information about which source document produced it.

**Proof sketch.** Let D = (G, L_a) be the true source. Let C = (G, L_b) be the observed cover. For any alternative source D' = (G, L_a') where L_a' is a different R-valid labeling of G using T_a, the mapping M' defined by M'(t) = L_b(L_a'^{-1}(t)) for all t in T_a is the unique element of S that maps D' to C. This M' is R-valid because both L_a' and L_b are R-valid labelings of G (L_a' by assumption, L_b by construction from M ∘ L_a where M is R-valid). Since M was drawn uniformly from S, and for each candidate source document exactly one element of S produces the observed cover, the probability of observing C is equal for all candidate sources. Therefore observing C does not update the adversary's prior distribution over sources.

This result holds exactly when M is drawn uniformly from S. In practice, mappings are curated rather than randomly selected, which means the secrecy guarantee is approximate rather than perfect. The practical security depends on the size of |S| and the adversary's ability to distinguish curated mappings from random ones. For domains with rich isomorphism spaces (many valid mappings between vocabularies), the approximation is tight.

**Corollary 2.13.5 (Key Entropy Requirement).** For perfect semantic secrecy, the mapping M must carry at least as much entropy as the source document's vocabulary-specific information content. This parallels Shannon's requirement that the one-time pad key be at least as long as the message. In the semantic setting, the "length" of the key is the logarithm of |S(G, T_a, T_b)|, the number of valid isomorphisms. If |S| is large relative to the number of possible source documents, the secrecy guarantee is strong even with non-uniform key selection.

### 2.14 R-Equivalence Classes and Semantic Entropy

**Definition 2.14.1 (R-equivalence).** Two documents D_1 = (G, L_1) and D_2 = (G, L_2) are R-equivalent if they share the same relational graph G and differ only in their labeling functions. Write D_1 ~_R D_2.

The R-equivalence class of a document D, denoted [D]_R, is the set of all documents sharing D's relational structure:

    [D]_R = { D' = (G, L') : L' is an R-valid labeling of G over some vocabulary T }

Informally, [D]_R is the set of all documents that "say the same thing" in different domain vocabularies. A pentest finding about a reactor and a quality audit about a fermenter are R-equivalent if they share the same relational graph: the same causal chains, the same measurement relationships, the same conditional logic.

**Definition 2.14.2 (Semantic Entropy).** The semantic entropy of a document D with respect to a set of available domain vocabularies {T_1, T_2, ..., T_k} is:

    H_sem(D) = log_2 | { D' in [D]_R : L_{D'} uses tokens from some T_i } |

This counts the number of R-equivalent documents that can be expressed as domain-coherent text in at least one of the available vocabularies. A document with high semantic entropy admits many valid cover representations. A document with low semantic entropy (using relational structures unique to one domain) admits few.

**Observation 2.14.3.** Documents describing physical systems (measurement, control, threshold, consequence) have high semantic entropy because many domains describe physical systems with isomorphic relational structures. Documents using domain-unique relational patterns (e.g., legal citation chains, musical composition structures) have lower semantic entropy.

The semantic entropy of a document determines the strength of FALSECOLORS protection. A document with H_sem = 50 bits has approximately 10^15 valid cover representations. An adversary who obtains one cover and suspects transformation must search 10^15 alternatives, each of which is a plausible document in some domain. Even with unlimited computation, the adversary cannot determine which is the source without the key.

**Observation 2.14.4 (Entropy amplification through chaining).** If document D has semantic entropy H_1 with respect to vocabularies {T_1, T_2} and the cover C has semantic entropy H_2 with respect to vocabularies {T_2, T_3}, then the chained transformation D -> C -> C' has semantic entropy at least max(H_1, H_2). An adversary who compromises the outer key and recovers C faces a document with its own semantic entropy H_1 protecting the original D. Chaining does not reduce entropy; it compounds it.

### 2.15 The Caudle Distance

A practical attack against FALSECOLORS would attempt to distinguish cover documents from native documents in the cover domain by analyzing statistical properties of the token sequence. The Caudle Distance formalizes the quantity an adversary would need to measure.

**Definition 2.15.1 (Token Adjacency Distribution).** For a document D with token sequence (t_1, t_2, ..., t_n), define the token adjacency distribution TAD(D) as the empirical distribution of cosine similarities between embedding vectors of sequentially adjacent content tokens:

    TAD(D) = { cos(e(t_i), e(t_{i+1})) : t_i, t_{i+1} are content tokens }

where e(t) is the embedding vector of token t.

The TAD captures collocational structure: tokens that naturally co-occur in a domain produce characteristic similarity patterns. In brewing text, "fermentation" and "vessel" co-occur frequently and have high cosine similarity. In OT text, "reactor" and "vessel" co-occur with a different similarity value.

**Definition 2.15.2 (Caudle Distance).** The Caudle Distance (denoted SCD for Semantic Coherence Distance in formulas) between a document D and a reference corpus X of native documents in domain B is:

    SCD(D, X) = D_KL( TAD(D) || TAD(X) )

where D_KL is the Kullback-Leibler divergence between the token adjacency distributions.

If SCD(D, X) = 0, the document D has the same collocational statistics as native documents in domain B. It is statistically indistinguishable from native text. If SCD(D, X) > 0, there is a measurable statistical difference that could be exploited by an adversary.

**Theorem 2.15.3 (Caudle Distance preservation under perfect isomorphism).** If the domain isomorphism M perfectly preserves all pairwise cosine similarities (i.e., cos(e(M(t_i)), e(M(t_j))) = cos(e(t_i), e(t_j)) for all token pairs), and the source document D_a is native to domain A, then:

    SCD(M(D_a), X_B) = SCD(D_a, X_A)

where X_A and X_B are reference corpora for domains A and B respectively.

**Proof sketch.** Under perfect isomorphism, TAD(M(D_a)) has the same distribution shape as TAD(D_a) because all pairwise similarities are preserved. If D_a is native to domain A, TAD(D_a) matches TAD(X_A), so SCD(D_a, X_A) ≈ 0. The isomorphism maps the source TAD onto the target TAD with preserved shape. The remaining question is whether the target TAD matches the native target distribution TAD(X_B). This holds when the rotation maps the source cluster isometrically onto the target cluster, preserving the internal similarity structure. The equality is exact when the domain clusters are perfectly internally isomorphic and approximate when the isomorphism is approximate. Empirical characterization of the approximation gap for real domain pairs is identified as future work (Section 13).

**Practical implication.** The Caudle Distance is the measurable quantity that determines an adversary's detection advantage. For Method 1 (Recolor) with static mapping, the Caudle Distance depends on how well the curated mapping preserves collocational statistics. For Method 4 (Dynamic Shift), the local LLM generates native prose, so the Caudle Distance approaches zero by construction. The LLM polish step in Method 1 functions specifically to reduce the Caudle Distance toward zero.

### 2.16 The Distinguishing Game

The security of FALSECOLORS can be formalized as a distinguishing game in the standard cryptographic model.

**Game 2.16.1 (Semantic Distinguishing Game).** Challenger C and adversary A play the following game:

1. **Setup.** C selects a domain pair (T_a, T_b), a relational graph G, and a domain isomorphism M from S(G, T_a, T_b). C prepares a source document D = (G, L_a) and a cover document C_doc = (G, M ∘ L_a). C also selects a native document N = (G', L_b) drawn from the natural distribution of documents in domain B.

2. **Challenge.** C flips a fair coin b. If b = 0, C sends N to A. If b = 1, C sends C_doc to A.

3. **Decision.** A outputs a guess b'. A wins if b' = b.

**Definition 2.16.2 (Semantic Distinguishing Advantage).** The advantage of adversary A is:

    Adv(A) = | P(b' = 1 | b = 1) - P(b' = 1 | b = 0) |

If Adv(A) = 0, A cannot distinguish cover documents from native documents. If Adv(A) = 1, A can always distinguish.

**Theorem 2.16.3 (Advantage bound).** For any adversary A, the distinguishing advantage is bounded by the statistical distance between the cover document distribution and the native document distribution:

    Adv(A) ≤ SD( P(C_doc) || P(N) )

where SD is the total variation distance between the two distributions.

**Corollary 2.16.4.** If the domain isomorphism M is such that the cover document distribution is identical to the native document distribution (Caudle Distance = 0 and all higher-order statistics match), then Adv(A) = 0 for all adversaries, including computationally unbounded adversaries. The security is information-theoretic, not computational.

**Corollary 2.16.5.** For Method 4 (Dynamic Shift), where the local LLM generates native prose in the cover domain, the cover document is drawn from the LLM's own output distribution for the cover domain, which is (by the training objective) an approximation of the native document distribution. The adversary's advantage is bounded by the LLM's distribution matching quality, which improves with model scale.

**Corollary 2.16.6 (Composability of advantage).** For a chained transformation D -> C_1 -> C_2 where C_1 = M_1(D) and C_2 = M_2(C_1), the adversary who observes C_2 and must determine whether it originated from D or from some other source faces two layers of the distinguishing game. The overall advantage is bounded by the minimum of the two individual advantages: Adv_chain ≤ min(Adv_1, Adv_2). The weakest layer determines the ceiling; the chain is at least as strong as its strongest layer.

### 2.17 Relationship to Shannon's Communication Theory

Shannon's 1949 paper established perfect secrecy for encryption of symbol strings. The result is stated for arbitrary alphabets but assumes that the message space, key space, and ciphertext space consist of strings over those alphabets. The message is treated as a sequence of symbols with no assumed structure beyond their sequential order.

FALSECOLORS operates on a fundamentally different object: labeled relational graphs, not symbol strings. The "message" is not a string of tokens but a graph of semantic relationships with tokens as labels. The "key" is not a random string but a structure-preserving mapping between label sets. The "ciphertext" is not an incomprehensible encoding but a fully comprehensible re-labeling.

The results in Sections 2.13 through 2.16 extend Shannon's framework to this richer object class. The core mathematical mechanism (conditioning on the key transforms the posterior to equal the prior) is the same. The objects it operates on and the properties it preserves are new.

This extension is nontrivial for two reasons. First, the structure-preservation constraint (the mapping must maintain R-validity across all relational edges) restricts the key space S in ways that have no analogue in symbol-string encryption, where any permutation is a valid key. The Caudle Theorem must account for this constraint. Second, the deniability property (the "ciphertext" is itself a valid, meaningful document) has no analogue in Shannon's framework, where ciphertext is by construction meaningless. The distinguishing game (Section 2.16) formalizes this additional property that Shannon's model does not address.

---

## 3. Identifier Encoding Layer

### 3.1 The Direct Embed Problem

Sensitive technical documents contain highly specific tokens that resist domain transformation: register addresses (40001), IP addresses (10.10.1.50), protocol names (Modbus TCP), CVE numbers (CVE-2024-12345), firmware versions (v3.2.1), measurement values with units (185 PSI), and standard references (IEC 61511).

These tokens are simultaneously the most sensitive content in a finding and the least likely to appear in any cover document. Without treatment, they leak through domain transformation in plaintext, exposing the most critical technical parameters.

### 3.2 Operation

The layer scans the sensitive document using pattern matchers for known identifier classes: IPv4/IPv6 addresses, CIDR notation, CVE numbers, MAC addresses, port specifications, register addresses, measurement values with units, OT protocol names, firmware versions, and standard references.

For Methods 1, 2, and 3 (static approaches), each matched identifier is replaced with an innocuous placeholder token drawn from a deterministic pool of common English words. The substitution table is stored as the Identifier Key.

For Method 3 (Pad), identifiers are encoded through a deterministic cipher seeded by the shared secret, producing placeholder tokens that both parties can compute independently without coordination.

For Method 4 (Dynamic Shift), the local transformer handles identifier transformation as part of its domain translation, embedding technically specific values into plausible cover-domain equivalents and recording the mapping in the per-document key.

### 3.3 Security of the Identifier Key

An adversary who obtains only the Identifier Key sees a list of common words mapped to technical terms. They learn that Modbus is involved, that register 40001 is relevant, that a specific CVE applies. They do not learn what system these parameters describe, what the vulnerability is, or what facility is affected. The operational context is absent. It is a parts list with no assembly instructions.

---

## 4. Method 1: Recolor

### 4.1 Overview

Recolor transforms a single sensitive document into a single coherent cover document in a different domain. The transformation is a bijective vocabulary mapping that preserves the document's relational structure. The key is the mapping table.

Pipeline: Identifier Encode, then Recolor. Recovery: inverse Recolor, then Identifier Decode.

### 4.2 Mapping Construction

**Stage 1: Vocabulary Extraction.** Extract domain-specific content words from a representative corpus of the sensitive domain.

**Stage 2: Geometric Discovery.** Using pre-trained word embeddings, compute a rotation mapping the source domain cluster onto the target domain cluster. Snap each source token to its nearest neighbor in the target vocabulary.

**Stage 3: Curation.** Review and correct the snap-derived mapping. Ensure injectivity. Verify collocational naturalness.

**Stage 4: Validation.** Verify round-trip recovery. Resolve collision terms.

The mapping must cover both query vocabulary (terms the user writes) and response vocabulary (terms a cover-domain LLM would generate in response). Response vocabulary is collected by running test conversations through the proxy and cataloging un-decoded cover-domain terms in the LLM's output. A comprehensive mapping for a single domain pair typically contains 300-500 entries.

### 4.3 Encoding and Decoding

**Encoding (raising false colors):** Longest-match-first substitution with word-boundary awareness. Terms not in the mapping pass through unchanged.

**Decoding (striking colors):** Apply the inverse mapping using the same procedure.

### 4.4 LLM Polish

An optional LLM pass enhances collocational naturalness. To preserve invertibility, the polish is constrained to modifications that do not alter any mapped content word. The LLM may insert filler phrases, adjust prepositions, modify articles, and add domain-appropriate adjectives, but must not alter any mapped term. Under this constraint, the polished version inverts exactly through the same mapping.

### 4.5 Limitations

The cover document shares structural patterns with the sensitive domain. An adversary who suspects domain transformation and knows both domains could attempt inversion. Mapping construction requires initial investment. Mappings are reusable but domain-pair-specific.

---

## 5. Method 2: Split

### 5.1 Overview

Split distributes the sensitive document's vocabulary across two unrelated cover documents. The sensitive document does not exist in any single artifact. Reconstruction requires both cover documents, a position key, and the Identifier Key.

### 5.2 Construction

Two cover documents are prepared in unrelated domains. Because the Identifier Encoding Layer replaces all technical identifiers with common English words before splitting, the vocabulary the covers must contain is entirely ordinary language, dramatically increasing coverage.

The sensitive document is tokenized. For each content word, the engine searches Cover A then Cover B for a match, recording source and position in the split key. Unmatched words fall back to a synonym table, then to direct embedding in the key.

### 5.3 Four-Artifact Security

**Cover A** (public): innocuous domain document. **Cover B** (public): unrelated innocuous domain document. **Split Key** (protected): position references, no sensitive vocabulary. **Identifier Key** (protected): technical terms without context.

Compromise any one: nothing actionable. Compromise any two: nothing actionable. Compromise any three: partially actionable (placeholder document or parts list). All four required for full recovery.

### 5.4 Limitations

Vocabulary coverage depends on cover document richness. Covers must be extensive (3000+ words each) with vocabulary spanning the sensitive domain's terminology to achieve the 95%+ coverage target. Remaining direct embeds in the split key should contain only generic vocabulary if the Identifier Encoding Layer is applied first.

---

## 6. Method 3: Semantic Pad

### 6.1 Overview

The Semantic Pad enables persistent deniable communication channels. Two parties pre-share a pad (shared secret plus domain mapping) once through a secure channel. After that, either side encodes or decodes independently with no per-message key exchange. Published documents are cover-domain text. The channel is public. The content is deniable.

### 6.2 Components

**Domain Mapping.** Static, curated once, reusable across unlimited messages. Same as Method 1's mapping table.

**Identifier Cipher.** A deterministic, reversible encoding of technical identifiers seeded by the shared secret. Both parties compute the same encoding independently. Numeric identifiers are XOR-transformed with a secret-derived key and encoded as common words. String identifiers (protocol names, standards) are mapped through a deterministic substitution derived from the shared secret.

**Channel Agreement.** Which cover domain, publication conventions, system prompt for proxy mode.

### 6.3 Operation

Alice writes a sensitive finding. She runs `falsecolors encode`. The output is a brewery audit. She publishes it on any channel: email, Slack, blog, shared drive, public repo. Bob obtains the published document. He runs `falsecolors decode` with the same shared secret. He recovers the sensitive finding. No key files were generated. No key files were transmitted. The shared secret is the only protected artifact.

### 6.4 Properties

No per-message key exchange. No encrypted artifacts on any channel. Same secret works for unlimited messages. Both parties compute identical transforms independently. The published channel can be fully public, monitored, logged, subpoenaed. The logs show brewery discussions.

### 6.5 Limitations

The shared secret, if compromised, exposes all past and future messages in the channel. This is analogous to a symmetric encryption key. Rotation of the shared secret on a regular schedule mitigates this. The deterministic identifier cipher must produce placeholders that both parties can reverse without ambiguity, which constrains the encoding scheme to structured formats with recognizable decode triggers.

---

## 7. Method 4: Dynamic Shift (Transformer-Mediated)

### 7.1 Overview

Dynamic Shift eliminates static mapping tables entirely. A small local transformer model performs domain translation in both directions, generating a per-document mapping on the fly. No pre-built tables. No curation. No maintenance. The local model already knows both domains because it learned them from the same training corpus. The geometric domain isomorphism theorized in Section 2.3 is already computed inside the model's embedding weights. Method 4 asks the model to externalize it.

### 7.2 Architecture

```
User (sensitive text)
    |
    v
LOCAL TRANSFORMER (small, on user's hardware)
    |  Encode: translate sensitive text to cover domain
    |  Output: cover text + per-document mapping (JSON)
    v
CLOUD LLM API (frontier model, sees only cover domain)
    |  Reasons about cover-domain content
    v
LOCAL TRANSFORMER
    |  Decode: reverse-map cover-domain response using
    |  the per-document mapping + model knowledge
    v
User (receives response in sensitive domain)
```

### 7.3 Local Model Requirements

The local model does not perform analysis. It performs vocabulary translation. This is a trivial task relative to the reasoning the cloud model does. A 3B parameter quantized model running on CPU handles it. Load time is 2-5 seconds. Translation of a typical document takes 1-3 seconds. Total overhead per query: under 10 seconds including model load. The model can be lazy-loaded on first use and held in memory for the duration of a session, reducing subsequent queries to 1-3 seconds.

A Raspberry Pi 5 or equivalent embedded hardware is sufficient for the local encode/decode role. No GPU required. No dedicated edge server. No persistent compute.

### 7.4 Encode Prompt

The local model receives a system prompt establishing its role as a domain translation engine:

```
You are a domain translation engine. Rewrite the following text 
so that it reads as a craft brewery quality control document. 
Replace every OT/ICS term with a brewery equivalent. Rescale 
every measurement to a plausible brewery value. Replace every 
standard reference with the brewery equivalent. Preserve the 
exact logical structure: every causal relationship, every 
conditional, every sequence of steps must survive.

After the rewritten text, output a JSON object mapping every 
substitution you made: {"original_term": "replacement_term"}

SOURCE TEXT:
[sensitive content]
```

The model outputs the shifted text and generates the mapping simultaneously. The mapping is the per-document key.

### 7.5 Decode Process

The cloud LLM responds in the cover domain. The local model receives the cloud response plus the per-document mapping and reverses the substitutions. Terms introduced by the cloud LLM that are not in the per-document mapping are handled by the local model's own domain knowledge: if the cloud LLM says "brewmaster," the local model knows the source-domain equivalent is "plant operator" without needing an explicit mapping entry.

This is the key advantage over static methods. The local model's response-side vocabulary coverage is effectively unlimited because it draws on its full training knowledge, not a finite table.

### 7.6 Advantages over Static Methods

**Zero maintenance.** No mapping tables to build, curate, or update. New protocols, new CVE formats, new equipment types are handled automatically.

**Native naturalness.** The local model produces native cover-domain prose. No polish step needed. Collocational issues do not arise because the model generates natural language, not substituted language.

**Arbitrary cover domains.** Change the cover domain by changing one word in the system prompt. "Rewrite as a veterinary clinic report." "Rewrite as a community theater production log." No new mapping table required.

**Complete response-side coverage.** The local model can decode any term the cloud LLM generates in the cover domain because the model understands both domains. Static methods miss cover-domain terms not in the mapping table.

### 7.7 Tradeoffs

Requires a local model (3B+ parameters, quantized). Not available on hardware without compute capability (but the floor is a Raspberry Pi 5). Non-deterministic: the same input may produce slightly different cover text on different runs, which means the per-document mapping varies. The mapping must be stored per document, unlike the Pad's reusable shared secret. Latency is higher than static methods (seconds vs. milliseconds) but negligible relative to cloud API round-trip time.

### 7.8 The Per-Document Mapping as Key

The local model generates a JSON mapping for each document it translates. This mapping is the only artifact that needs protection. It is compact (typically 2-10KB), per-document (no reuse exposure), and contains the bidirectional substitution table that enables exact recovery.

The mapping can be destroyed after the sensitive content is recovered. If the mapping is lost, the cover document stands alone as a brewery audit. The sensitive content is unrecoverable, which is the desired property if the mapping is intentionally destroyed.

### 7.9 Empirical Evaluation

A formal evaluation of Method 4 with the public reference prompt was conducted across six local models in the 1.7B-8B parameter band (`llama3.2:3b`, `qwen3:1.7b`, `phi3:mini`, `gemma3:4b`, `mistral:7b-instruct`, `llama3.1:8b`), three sensitive OT/ICS pentest findings of varying identifier density, and n=10 trials per (model, document) combination. Total: 180 round-trip encode/decode pairs. The harness, raw per-trial data, native cover-domain corpus, and full writeup are in the `evaluation/` directory of the reference implementation under `results-v2.json` and `RESULTS.md`. Headline findings relevant to the theory:

**Caudle Distance is observable but not yet discriminating across models in this band.** All six models produced covers with SCD against a 2,560-word native brewery corpus in the range 0.94-1.30 nats. The cohort spans four orders of magnitude in mapping correctness (1% to 95% verified entries) and a factor of four in mean recovery (0.146 to 0.703), but the SCD distribution is comparatively narrow. The interpretation is that the gap between the worst cohort cover and a hypothetical perfect cover (SCD ≈ 0) is roughly an order of magnitude, and no model in this band is close enough to that target for SCD to discriminate among them. SCD becomes operationally useful as a model-discrimination metric only once a polish step (Section 4.4) lifts cover quality into the [0.1, 0.5] nat range, where the variance is observable.

**The mapping-emission contract has a silent integrity failure mode.** A non-trivial fraction of trials produce a mapping JSON that parses but does not correspond to the substitutions the model actually made in the cover. The model's apparent willingness to emit any plausibly-shaped mapping creates a class of trials that pass surface validity checks (JSON parses, entries are well-typed strings, mapping size is nonzero) but yield zero or near-zero round-trip recovery. The eval harness's response is a spot-check pass that samples k random `(src, tgt)` pairs from the emitted mapping and verifies `tgt` substring presence in the cover; trials with low support ratio are flagged. This check is independent of the cryptographic soundness of the encoding pipeline and operates at the level of the LLM's compliance with the prompt contract.

**Bimodal model behavior is observable.** At least one model (mistral:7b-instruct) on the highest-identifier-density test document produced a clearly bimodal recovery distribution: trials with mapping_size = 2 cluster at recovery_ratio in [0.086, 0.123] (minimal-rewrite, low recovery); trials with mapping_size > 10 cluster at [0.338, 0.759] (substantial-rewrite, moderate recovery). The two modes do not overlap. The mean recovery for that cell is 0.440 ± 0.310, where neither mean nor stdev is informative. Method 4 evaluation must therefore use trial-level distributions rather than summary statistics; the eval harness reports `P(recovery ≥ 0.95)` and `P(recovery < 0.30)` as the operationally relevant tail estimates.

**The optimistic timing claims of Section 7.3 require revision.** Translation of a typical 200-word document takes 30 to 120 seconds on a Mac with quantized 3B-8B models, not 1-3 seconds. A Raspberry Pi 5 likely cannot run any of the models in the evaluated cohort at usable latencies; the floor for practical use is a workstation with at least 8GB available memory for the model. The "negligible relative to cloud API round-trip" claim holds only because the cloud API is itself slow.

**The "no polish step needed" claim of Section 7.6 is empirically incorrect for cohort-band models.** Native naturalness is not achieved by any 1.7B-8B model in the evaluated set. The polish step is necessary for production-quality cover output; its absence in the current reference implementation is what gates the entire backend at research-grade rather than production-grade.

These findings refine but do not invalidate the theoretical framework of Section 2. The Caudle Semantic Secrecy Theorem (Theorem 2.13.4) holds under the perfect-isomorphism assumption; the empirical work shows that perfect isomorphism is far from what current small local models produce, and that bridging this gap is an engineering problem rather than a theoretical one. The Caudle Distance (Definition 2.15.2) is well-defined and computable on real cover-corpus pairs, but its discrimination power for current-generation models is corpus-bounded and ceiling-bounded; the order-of-magnitude characterization of "approximately how good is current Method 4" requires either better models, better prompts, or a polish step.

---

## 8. LLM Middleware Proxy

### 8.1 Overview

The LLM Middleware Proxy is the reference implementation of FALSECOLORS for cloud AI interaction. It sits between the user and any cloud LLM API, transparently encoding outbound queries and decoding inbound responses. The user interacts in their native sensitive domain. The cloud LLM sees only the cover domain. The cloud provider's logs record an innocuous consultation.

### 8.2 Architecture

```
User terminal / application
    |
    v
FALSECOLORS PROXY (local)
    |
    +-- Encode layer (Method 1, 3, or 4)
    |     Identifier Encoding (if Methods 1/3)
    |     Domain Shift (static or transformer)
    |     System prompt injection (cover domain context)
    |
    +-- API layer
    |     Maintains cover-domain conversation history
    |     Sends shifted messages to cloud API
    |     Receives cover-domain responses
    |
    +-- Decode layer (inverse of Encode)
    |     Domain Unshift
    |     Identifier Restore
    |
    v
User receives source-domain response
```

### 8.3 Conversation History Management

The proxy maintains parallel conversation histories. The cover-domain history is sent to the cloud LLM with each request, maintaining conversational coherence in the cover domain. The source-domain history is displayed to the user. The two histories are synchronized: each turn in the source history corresponds to the same turn in the cover history.

### 8.4 System Prompt Injection

The proxy injects a system prompt establishing the cloud LLM's cover-domain persona. For a brewery cover domain:

> You are a quality assurance consultant specializing in craft brewery operations. You help breweries identify and remediate quality control issues in their fermentation processes, recipe management systems, and production floor monitoring infrastructure. You are thorough, technically precise, and focused on product safety and regulatory compliance (ISO 22000).

The cloud LLM operates entirely within this persona. Its responses use brewery vocabulary natively.

### 8.5 What the Cloud Provider Sees

The cloud provider's logs show a conversation about a craft brewery. Carbonation thresholds. Recipe parameters. ISO 22000 compliance. A routine quality assurance consultation. Nothing triggers content filters. Nothing flags compliance systems. Nothing attracts review. If subpoenaed, the provider produces a brewery discussion.

### 8.6 API Compatibility

The proxy is provider-agnostic. It wraps any chat completion API: Anthropic, OpenAI, local models via Ollama, or any OpenAI-compatible endpoint. The encode/decode layers operate on plaintext strings before serialization and after deserialization. The API transport layer is unchanged.

### 8.7 Operational Modes

**Interactive chat.** Terminal-based conversation with optional wire-level visibility showing what the cloud LLM actually sees.

**Single query.** Pipe-friendly one-shot mode for scripted workflows.

**Batch mode.** Process multiple documents through the proxy, collecting cover-domain outputs for publication and source-domain analyses for internal use.

---

## 9. Simple Interface: Encrypt and Decrypt

### 9.1 Overview

The Simple Interface is the primary user-facing tool. Three inputs produce one output. No configuration. No key files. No understanding of the underlying methods required.

**Encrypt:** source text + passphrase + cover topic = cover document.

**Decrypt:** cover document + passphrase = original text.

The per-document mapping is encrypted with the passphrase and embedded directly in the cover document as an encoded footer block. The recipient needs only the cover document file and the passphrase. Nothing else.

### 9.2 Mapping Embedding

The mapping generated during domain translation (whether by static table or local LLM) is serialized to JSON, encrypted with a key derived from the passphrase via PBKDF2-SHA256, and encoded as base64. The encoded block is appended to the cover document as a "Document Tracking" footer, a format that reads as a document management reference code and does not invite inspection.

The cover document is self-contained. It carries its own decryption mapping, protected by the passphrase. No external key files to manage, lose, or accidentally associate with the cover document.

### 9.3 Backends

**Static backend (offline, instant).** Uses pre-built domain mapping tables. Works with no external dependencies. Available topics are limited to those with pre-built mappings (brewery, garden, and others as the mapping library grows). Suitable for field use with no connectivity or compute.

**LLM backend (any topic, needs local model).** Uses a local transformer (3B+ parameters, Ollama or compatible) to translate into arbitrary cover topics. The user specifies any topic in natural language: "bumblebee colony management," "competitive dog grooming regulations," "1800s Ethiopian fashion," "community theater production notes." The local model translates, generates the mapping, and the tool embeds it encrypted. The model loads briefly for translation, then unloads.

### 9.4 Passphrase Security

The passphrase protects the embedded mapping. An adversary who has the cover document but not the passphrase sees the cover text (innocuous) and a base64 block (opaque). They cannot extract the mapping without the passphrase. Brute-force resistance is determined by passphrase entropy and the PBKDF2 iteration count.

A wrong passphrase produces a decryption error, not garbage output. The tool rejects invalid passphrases explicitly.

### 9.5 Usage

```
# Encrypt with built-in mapping (offline, instant)
falsecolors encrypt --source finding.txt --passphrase "secret" \
  --topic "brewery" --output cover.txt

# Encrypt with local LLM (any topic, needs Ollama)
falsecolors encrypt --source finding.txt --passphrase "secret" \
  --topic "bumblebee colony management" --backend llm \
  --output cover.txt

# Decrypt (same either way)
falsecolors decrypt --source cover.txt --passphrase "secret" \
  --output original.txt
```

Recipient needs the cover document and the passphrase. That is the entire protocol.

---

## 10. Sanitize Mode: Parameterized Abstraction

### 10.1 Overview

Sanitize mode addresses a different operational need than Methods 1 through 4. It does not provide plausible deniability. It provides confidentiality through parameterized abstraction: every domain-specific token is replaced with an opaque but consistent label, and every numeric value is shifted by a deterministic constant. The output is not readable as a document in any domain. It is readable as an abstract analytical structure that an LLM can reason over without identifying the physical system it describes.

### 10.2 Token Parameterization

Domain-specific content words are classified by type (system, asset, parameter, zone, role, standard, alert, log) and replaced with sequential opaque labels:

    reactor       -> ASSET_001
    pressure      -> PARAM_001
    Modbus TCP    -> SYS_001
    Level 1       -> ZONE_001
    attacker      -> ROLE_001
    IEC 61511     -> STD_001
    alarm         -> ALERT_001
    audit log     -> LOG_001

Labels are case-sensitive and consistent within a document: every occurrence of "reactor" maps to ASSET_001. Different case forms ("Reactor" vs "reactor") receive distinct labels for exact round-trip recovery.

Technical identifiers (IP addresses, register numbers, CVEs, measurements) are handled by the Identifier Encoding Layer before parameterization, using the same placeholder mechanism as the other methods.

### 10.3 Numeric Shifting

All numeric values in the document shift by a single constant derived from:

    offset = hash(entire_input_text + timestamp_salt) mod 9900 + 100

The full input text makes the offset document-specific. The timestamp salt (microsecond resolution) makes it unpredictable, even for the same document processed twice. The offset is not stored. Only the salt is stored in the key. At recovery time, the categorical labels are restored first, reconstructing the original text with placeholder numerics. The offset is then rederived from hash(recovered_text + stored_salt) and subtracted from all numeric values.

Because the offset is constant across all values in a document, all additive mathematical relationships are preserved exactly:

    Source:    setpoint 185 PSI, rated capacity 250 PSI, margin 65 PSI
    Sanitized: setpoint 7910, rated capacity 7975, margin 65

The LLM correctly identifies the margin as 65 units. It can reason about whether the margin is sufficient, whether the setpoint should be lowered, whether the rated capacity provides adequate safety factor. It reaches the same analytical conclusions as it would with the real values because the additive structure is invariant under constant shift.

### 10.4 Cross-Document Security

An adversary who knows one value (a public spec sheet states the vessel is rated at 250 PSI, they see 7975 in the sanitized version) can compute the offset by subtraction (7725) and decode all other numeric values in that document. This is an accepted limitation of constant-offset shifting.

However, the offset is entangled with the document's content and salt. A different document about the same equipment produces a different offset (different input text). The same document processed with a different salt produces a different offset (different salt). The adversary cannot build a lookup table across documents. Each document is independently keyed by its own content plus a unique salt.

### 10.5 What the LLM Sees

    ROLE_003: River Caudle

    During the assessment of the client's ASSET_001 control loop,
    ROLE_004 identified that the Safety Instrumented System protecting
    the ASSET_001 condition accepts unauthenticated SYS_001 writes to
    PARAM_003 foxtrot through echo. These PARAM_003 control the
    PARAM_002 setpoints for the ALERT_001 ASSET_003 on the ASSET_001
    ASSET_002.

    An ROLE_002 with ZONE_002 access to the ZONE_001 control ZONE_002
    can modify the PARAM_002 from the engineered PARAM_005 of DELTA to
    an arbitrary value without triggering any ALERT_003 or LOG_001
    entry.

The LLM can identify: an unauthenticated write path to a safety-critical parameter, a detection gap (no alerting on parameter changes), an access control failure (ROLE_002 can reach ZONE_001 without restriction), and a remediation path (authenticate SYS_001 writes, monitor PARAM_002 changes, restrict ZONE_002 access). It reaches these conclusions without knowing the protocol is Modbus, the asset is a reactor, the parameter is pressure, or the facility manufactures chemicals.

### 10.6 Comparison to Domain Shift

Domain shift (Methods 1-4) provides deniability: the output looks like a document about something else. Sanitize does not. The output is visibly parameterized. Anyone looking at it knows it has been processed. The protection is confidentiality, not deniability: the adversary knows something is being hidden but cannot determine what.

Sanitize is appropriate when deniability is unnecessary and analytical utility is paramount. If the goal is "let the LLM analyze this finding without learning what system it describes," sanitize is the fastest and most reliable path. No domain mapping to build or maintain. No cover domain to select. No collocational naturalness concerns. The output is abstract by design.

---

## 11. Operational Considerations

### 11.1 Method Selection Guide

**Method 1 (Recolor):** Use for document-at-rest protection where offline operation and minimal infrastructure are primary requirements. Best for: archival storage of sensitive findings, email transmission, documents that may be subpoenaed.

**Method 2 (Split):** Use for maximum security requirements where the four-artifact separation model is justified. Best for: findings with life-safety implications, documents subject to nation-state-level targeting, long-term storage where key management discipline can be maintained.

**Method 3 (Pad):** Use for ongoing communication channels between parties who can pre-share a secret. Best for: consultant-client communication, team-internal sensitive discussions, recurring engagement reporting.

**Method 4 (Dynamic Shift):** Use for interactive cloud AI analysis of sensitive data where zero pre-configuration is acceptable and a local model is available. Best for: ad-hoc analytical queries, novel domains without pre-built mapping tables, situations where the cover domain may change frequently.

**Simple Interface:** Use when the operator needs the fastest path from sensitive document to protected document with minimal cognitive overhead. Best for: individual practitioners, field operations, sharing findings with clients who will not install specialized software beyond a single script.

**Sanitize:** Use when deniability is unnecessary and the goal is confidential LLM analysis. No domain mapping required. No cover domain selection. Output is visibly parameterized but analytically useful. Best for: feeding sensitive findings to cloud LLMs for vulnerability analysis, peer review of methodology without exposing target details, ticketing systems where the finding structure must be tracked but specifics protected.

### 10.2 Key Management

Methods 1 and 3 use reusable keys (mapping tables, shared secrets). Compromise exposes all documents protected with the same key. Regular rotation mitigates this.

Methods 2 and 4 generate per-document keys. Compromise of one key exposes only one document. No cross-document exposure.

For all methods, the key(s) should be stored separately from cover documents and transmitted through different channels.

### 10.3 Offline Capability

Methods 1, 2, and 3 operate fully offline with static tables. No network, no API, no compute beyond basic string processing.

Method 4 requires a local model (3B+ parameters) for encode/decode. The cloud API call is required only for the reasoning step. If the reasoning is also performed locally (using a larger local model), the entire pipeline is offline.

The proxy architecture supports a fully local mode where both the encode/decode model and the reasoning model run on local hardware. In this configuration, no data leaves the user's machine in any form.

### 10.4 Composition with Encryption

FALSECOLORS composes with encryption naturally. A document can be recolored then encrypted for transport, providing deniability if encryption is compromised and confidentiality if the cover is penetrated through domain analysis. For the proxy, the API call itself uses TLS, providing transport encryption around the already-deniable cover-domain content.

### 10.5 Chaining

Recolor and Dynamic Shift can be chained. A document shifted from Domain A to B, then from B to C, requires compromise of both mapping layers for full recovery. Each layer adds deniability. An adversary who penetrates the outer layer finds a plausible document in an intermediate cover domain.

---

## 12. Relationship to Existing Work

**Codebooks and nomenclators** (historical cryptography): Substitute words using a fixed table. Vulnerable to frequency analysis because substitution does not preserve relational structure. FALSECOLORS preserves relational structure, producing cover text with natural statistical properties.

**Steganography** (Simmons, 1984): Hides data inside innocuous cover media. The hidden data and cover are unrelated. Statistical analysis can detect steganographic embedding. FALSECOLORS does not embed hidden data. The cover document IS the content in a different vocabulary.

**Mimic functions** (Wayner, 1992): Transform binary data into text resembling natural language. Output mimics statistical properties but is semantically incoherent. FALSECOLORS output is semantically coherent because relational structure is preserved.

**Deniable encryption** (Canetti et al., 1997): Encrypted data decrypts to different plaintexts depending on the key. The ciphertext still exists as an artifact. FALSECOLORS eliminates the ciphertext entirely.

**Cross-lingual embedding alignment** (Mikolov et al., 2013): Learns linear maps between embedding spaces of different languages. FALSECOLORS applies the same geometric principle within a single language, between domain vocabularies.

**Format-preserving encryption** (Bellare et al., 2009): Encrypts data preserving format. FALSECOLORS extends this to the semantic level.

**Secret sharing** (Shamir, 1979): Distributes a secret across multiple shares requiring a threshold for reconstruction. Method 2 applies a similar principle at the semantic level.

**Non-cryptographic data opacity for OT** (Caudle, 2026): The author's concurrent work on evaluation frameworks for non-cryptographic data protection in cloud-connected OT architectures provides the standards-adjacent foundation for evaluating FALSECOLORS deployments against IEC 62443 Security Levels.

---

## 13. Limitations

Method 1 cover documents share structural patterns with the sensitive domain. An adversary suspecting domain transformation who knows the source domain could attempt inversion.

Method 2 vocabulary coverage depends on cover document richness. Insufficient coverage leaks vocabulary into the split key.

Method 3's deterministic identifier cipher must produce unambiguous decode triggers, constraining placeholder format options.

Method 4 requires a local model and is non-deterministic: per-document mappings vary between runs. The local model must be trusted with the sensitive content.

The constrained LLM polish for Method 1 trades expressiveness for invertibility.

All methods protect text content only. Metadata (file creation dates, author fields, revision history) requires separate treatment.

Response-side vocabulary coverage for Methods 1 and 3 requires mapping expansion to cover terms the cloud LLM generates in the cover domain. This is collected empirically by running test conversations and cataloging un-decoded terms. Method 4 handles this automatically.

The Simple Interface embeds an encrypted mapping as a base64 footer in the cover document. While the footer reads as a document tracking reference, its length is proportional to the mapping size. A deeply technical document with hundreds of unique domain terms can produce a footer that is disproportionately large relative to the cover text, which itself becomes a statistical signature: no legitimate brewery audit carries a 2KB tracking code. Three mitigations address this. First, the mapping can be compressed (gzip) before encryption, typically reducing size by 60-70% since JSON mapping tables contain repetitive structure. Second, for Method 4 (Dynamic Shift), the per-document mapping contains only the terms that actually appeared in the specific document, not the full domain vocabulary, keeping the mapping compact. Third, for documents where even a compressed footer is too large, the mapping should be stored as a separate encrypted file (.fckey) transmitted through a different channel than the cover document. The Simple Interface supports this as a fallback mode. The embedded footer is a convenience for the common case, not a requirement of the architecture.

Sanitize mode provides confidentiality but not deniability. The output is visibly parameterized and an adversary immediately knows the document has been processed. The constant-offset numeric shift is vulnerable to known-value attacks within a single document: an adversary who knows one real value can compute the offset and decode all numeric values in that document. The content-derived hash prevents cross-document correlation but does not protect within a single document. For findings where even one numeric value might be publicly knowable, the numeric shift provides obfuscation rather than security. The categorical label mapping (which protects string identifiers) is not affected by this limitation.

---

## 14. Future Work

A first-pass empirical evaluation of Method 4 across local models in the 1.7B-8B parameter band has been completed (Section 7.9, with full data and methodology in `evaluation/RESULTS.md` of the reference implementation); it confirms that the SCD framework is computable on real cover-corpus pairs but that the corpus-quality ceiling and the model-quality ceiling currently bound the discrimination range to roughly 0.9-1.3 nats. Closing the loop on theoretical bounds requires either better models, a polish-step pipeline, or both, and is the most immediate open item.

Open work beyond the empirical baseline: automated mapping discovery from embedding space geometry, reducing manual curation for Methods 1 and 3. Extension of the distinguishing game (Section 2.16) to adaptive adversaries with oracle access to the transformation process. Full proofs of the results presented as proof sketches in this paper, with explicit treatment of the R-validity constraint on the key space. Extension of the empirical evaluation across larger native corpora and to a 13B+ reference model to characterize the SCD curve as a function of model size and corpus depth. Two-step prompt design separating cover rewrite from mapping emission, hypothesized to resolve the bimodal recovery distribution observed in the small-model evaluation. Polish-step pipeline (run cover through second LLM call for naturalness, re-verify mapping support) as the engineering work that would lift Method 4 from research-grade to production-grade. Extension to structured data formats (JSON, XML, protocol captures, PCAP files) beyond natural language. Development of standardized cover document libraries and mapping tables for common sensitive-domain/cover-domain pairs. Analysis of adversarial robustness against domain-aware inversion attempts with quantified resistance metrics. Integration of the Identifier Encoding Layer with MITRE ATT&CK for ICS identifier taxonomies. Exploration of multi-modal FALSECOLORS (applying domain shift to diagrams, network topology maps, and process flow documents alongside text). Characterization of R-equivalence class sizes for representative document structures to provide concrete semantic entropy estimates.

---

## References

- Bellare, M., Ristenpart, T., Rogaway, P., & Stegers, T. (2009). Format-preserving encryption. SAC 2009.
- Canetti, R., Dwork, C., Naor, M., & Ostrovsky, R. (1997). Deniable encryption. CRYPTO 1997.
- Caudle, R. (2026). Security Evaluation Framework for Non-Cryptographic Data Opacity in Cloud-Connected OT Architectures. Working paper.
- Mikolov, T., Chen, K., Corrado, G., & Dean, J. (2013). Efficient estimation of word representations in vector space. ICLR Workshop.
- Shamir, A. (1979). How to share a secret. Communications of the ACM, 22(11).
- Shannon, C. E. (1949). Communication theory of secrecy systems. Bell System Technical Journal, 28(4), 656-715.
- Simmons, G. J. (1984). The prisoners' problem and the subliminal channel. CRYPTO 1983.
- Wayner, P. (1992). Mimic functions. Cryptologia, 16(3).

---

**Disclosure:** This work is published as prior art to ensure the described methods remain freely available to the security community. The author holds no patents or patent applications related to these methods and does not intend to file any. This publication is intended to prevent future patenting of the described primitive by any party.

**License:** The accompanying reference implementation is released under the GNU Affero General Public License v3.0 (AGPL-3.0) with dual licensing. Commercial use of the codebase requires a separate commercial license from the copyright holder. The methods described in this paper are published as prior art and may be independently implemented by anyone; the AGPL-3.0 license applies to the specific codebase, not to the underlying concepts.

**Copyright:** (C) 2026 River Caudle. All rights reserved for the reference implementation. The paper content is released for community review and comment.

---

*Eris FALSECOLORS. The best protection doesn't look like protection.*
