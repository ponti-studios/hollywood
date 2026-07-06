export const typeDefs = `schema {
  query: Query
  mutation: Mutation
}

# ── Scalars ──────────────────────────────────────────────────────────────────
scalar DateTime
scalar UUID
scalar Upload

# ── Queries ──────────────────────────────────────────────────────────────────
type Query {
  "Retrieve a single candidate by ID."
  candidate(candidateId: UUID!): Candidate!
  "List candidates with filtering, ordering, and pagination."
  allCandidates(projectId: UUID, filterBy: CandidateFilterInput, orderBy: CandidateOrderInput, offset: Int, limit: Int): [Candidate!]!
  "Retrieve a single project by ID."
  project(projectId: UUID): Project!
  "List all projects for the current user."
  allProjectsForUser: [Project!]!
  "List tags for a given project."
  projectTags(projectId: UUID!): [Tag!]!
  "Retrieve the current user."
  user: User!
  "Retrieve submissions for a given project."
  getSubmissions(projectId: UUID!): [Submission!]!
  "Search entities across the graph."
  search(query: String!, limit: Int, offset: Int): SearchResults!
}

# ── Mutations ────────────────────────────────────────────────────────────────
type Mutation {
  "Add one or more candidates to a project."
  addCandidates(projectId: UUID!, candidates: [CreateCandidateInput!]!): [Candidate]
  "Update one or more candidates."
  updateCandidates(projectId: UUID!, candidates: [UpdateCandidateInput!]!): [Candidate!]!
  "Delete candidates by ID."
  deleteCandidates(candidateIds: [UUID!]!): [DeletedCandidate!]!
  "Add a new project."
  addProject(project: CreateProjectInput!): Project!
  "Update an existing project."
  updateProject(project: UpdateProjectInput!): Project
  "Add a new user."
  addUser(user: CreateUserInput!): User!
  "Update an existing user."
  updateUser(user: UpdateUserInput!): User!
  "Create a user and project simultaneously."
  addUserAndProject(input: CreateUserAndProjectInput!): UserAndProject!
  "Delete a submission."
  deleteSubmission(submissionId: UUID!): Boolean!
  "Create a candidate from a submission."
  createSubmissionCandidate(submissionId: UUID!, position: String!): Candidate!
  "Add a script file to a candidate."
  addCandidateScript(projectId: UUID!, candidateId: UUID!, file: Upload!): Boolean!
  "Remove a script from a candidate."
  removeCandidateScript(scriptId: UUID!, candidateId: UUID!): Boolean!
  "Ingest a document for extraction."
  ingestDocument(text: String!, source: String): ExtractionResult!
}

# ── Entity Types ─────────────────────────────────────────────────────────────
"A person (writer, director, talent) in the entertainment graph."
type Candidate {
  id: UUID!
  name: String!
  agencyBio: String
  position: String!
  status: String!
  projectId: String!
  credits: [Credit!]!
  emails: [Email!]!
  phoneNumbers: [PhoneNumber!]!
  notes: [Note!]!
  representatives: [Representative!]!
  scripts: [Script!]!
  supportingLinks: [SupportingLink!]!
  tags: [CandidateTag!]!
  secondWriterName: String
  secondWriterEmails: [Email!]!
  secondWriterPhoneNumbers: [PhoneNumber!]!
  secondWriterSupportingLinks: [SupportingLink!]!
}

"A credit or role on a production."
type Credit {
  id: UUID!
  role: String!
  type: String
  production: String!
  network: String
  season: Int
  seasons: [Int!]!
  year: Int!
  years: [Int!]!
}

"An email address associated with a candidate."
type Email {
  address: String!
  contactType: String
}

"A phone number associated with a candidate."
type PhoneNumber {
  number: String!
  contactType: String
}

"A note or comment on a candidate."
type Note {
  id: ID!
  content: String!
  author: UUID!
  lastUpdated: DateTime!
}

"A representative (agent, manager, publicist) associated with a candidate."
type Representative {
  id: String!
  name: String!
  organization: String!
  representationType: RepresentationType
  emails: [Email!]!
  phoneNumbers: [PhoneNumber!]!
}

enum RepresentationType {
  AGENT
  MANAGER
  LAWYER
  PUBLICIST
  OTHER
}

"A script or sample attached to a candidate."
type Script {
  id: UUID!
  name: String!
  url: String!
  pageCount: Int!
  ratings: [Rating!]!
}

"A rating for a script."
type Rating {
  scriptId: UUID!
  raterUserId: UUID!
  score: Int!
}

"A link to supporting material."
type SupportingLink {
  url: String!
  description: String
  linkType: String
}

"A tag associated with a candidate."
type CandidateTag {
  id: UUID!
  label: String!
  tagger: String!
}

"A tag associated with a project."
type Tag {
  id: Int!
  tagName: String!
}

# ── Project ──────────────────────────────────────────────────────────────────
"A title, show, or production project."
type Project {
  id: UUID!
  title: String!
  season: Int!
  genres: [String!]!
  format: String
  imdbLink: String
  posterLink: String
}

# ── Submission ───────────────────────────────────────────────────────────────
"A document submission containing extracted candidate data."
type Submission {
  id: String!
  projectId: String!
  candidateId: String
  created: DateTime!
  submissionJson: SubmissionJson!
  samples: [SubmissionSample!]!
  rawSamples: [SubmissionSample!]!
}

"The extracted JSON payload from a submission document."
type SubmissionJson {
  name: String!
  bio: String
  email: String
  phoneNumber: String
  tags: [String!]
  organizations: [String!]
  credits: [SubmissionCredit!]
  representatives: [SubmissionRepresentative!]
  links: [SubmissionLink!]
  attachments: [String!]
}

"A credit within a submission payload."
type SubmissionCredit {
  role: String
  type: String
  production: String
  network: String
}

"A representative within a submission payload."
type SubmissionRepresentative {
  name: String
  title: String
  agency: String
  email: String
}

"A link within a submission payload."
type SubmissionLink {
  url: String
  type: String
}

"A sample document attached to a submission."
type SubmissionSample {
  id: String!
  submissionId: String!
  title: String!
  url: String!
  pageCount: Int!
}

# ── User ─────────────────────────────────────────────────────────────────────
"A platform user."
type User {
  id: UUID!
  name: String!
  title: String!
  userRole: String!
}

type UserAndProject {
  user: User!
  project: Project!
}

type DeletedCandidate {
  id: UUID!
}

# ── Hollywood Extensions ────────────────────────────────────────────────────
"Result of a document ingestion and extraction."
type ExtractionResult {
  id: UUID!
  candidates: [Candidate!]!
  modelName: String!
  rawJson: String!
}

"Search results across the entity graph."
type SearchResults {
  total: Int!
  entities: [Candidate!]!
  projects: [Project!]!
}

# ── Input Types ──────────────────────────────────────────────────────────────
input CandidateFilterInput {
  name: String
  firstName: String
  lastName: String
  position: [String!]
  status: [String!]
  tags: [String!]
  agencyBio: String
  secondWriterName: String
  exclude: [FilterExclude!]
}

input FilterExclude {
  field: String!
  value: String!
}

input CandidateOrderInput {
  orderItems: [OrderItemInput!]
}

input OrderItemInput {
  field: String!
  direction: String!
}

input CreateCandidateInput {
  name: String!
  agencyBio: String
  position: String
  credits: [CreditCreate!]
  emails: [EmailInput!]
  phoneNumbers: [PhoneNumberInput!]
  representatives: [RepresentativeCreateInput!]
  script: Upload
  secondWriterName: String
  secondWriterEmails: [EmailInput!]
  secondWriterPhoneNumbers: [PhoneNumberInput!]
  secondWriterSupportingLinks: [SupportingLinkInput!]
  status: String
  supportingLinks: [SupportingLinkInput!]
  tags: [String!]
  targetLevel: String
}

input EmailInput {
  address: String!
  contactType: String
}

input PhoneNumberInput {
  number: String!
  contactType: String
}

input CreditCreate {
  role: String!
  production: String!
  seasons: [Int!]
  years: [Int!]!
}

input CreditUpdate {
  id: ID!
  role: String
  production: String!
  seasons: [Int!]
  years: [Int!]
}

input CreditAction {
  additions: [CreditCreate!]
  updates: [CreditUpdate!]
  deletes: [ID!]
}

input UpdateCandidateInput {
  candidateId: ID!
  name: String
  agencyBio: String
  position: String
  status: String
  note: String
  credits: CreditAction
  emails: [EmailInput!]
  phoneNumbers: [PhoneNumberInput!]
  representatives: RepresentativeAction
  script: Upload
  secondWriterName: String
  secondWriterEmails: [EmailInput!]
  secondWriterPhoneNumbers: [PhoneNumberInput!]
  secondWriterSupportingLinks: [SupportingLinkInput!]
  supportingLinks: [SupportingLinkInput!]
  tags: TagAction
}

input RepresentativeCreateInput {
  name: String!
  organization: String
  emails: [EmailInput!]
  phoneNumbers: [PhoneNumberInput!]
  representationType: RepresentationType
}

input RepresentativeUpdateInput {
  id: ID!
  name: String
  organization: String
  emails: [EmailInput!]
  phoneNumbers: [PhoneNumberInput!]
  representationType: RepresentationType
}

input RepresentativeAction {
  additions: [RepresentativeCreateInput!]
  updates: [RepresentativeUpdateInput!]
  deletes: [ID!]
}

input TagAction {
  additions: [String!]
  deletes: [String!]
}

input SupportingLinkInput {
  url: String!
  description: String
  linkType: String
}

input CreateProjectInput {
  title: String!
  format: String
  genres: [String!]
  season: Int
  imdbLink: String
  image: Upload
  posterImage: Upload
  collaborators: [String!]
}

input UpdateProjectInput {
  id: UUID!
  title: String
  format: String
  genres: [String!]
  season: Int
  imdbLink: String
  image: Upload
  poster: Upload
}

input CreateUserInput {
  clerkUserId: String!
  emailAddress: String!
  name: String!
  role: String!
  title: String!
}

input UpdateUserInput {
  userId: UUID!
  fullName: String
  title: String
  userRole: String
}

input CreateUserAndProjectInput {
  user: CreateUserInput!
  project: CreateProjectInput!
}
`;
